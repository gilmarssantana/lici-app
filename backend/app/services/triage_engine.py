from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from app.schemas.case import CaseCreate
from app.schemas.decision import DecisionCriteria, DecisionRequest, MemorySuggestion
from app.schemas.radar import RadarOpportunity
from app.schemas.triage import (
    TriageItem,
    TriageLogsResponse,
    TriageMarkRequest,
    TriageMarkResponse,
    TriageQueueResponse,
    TriageRunLog,
    TriageRunRequest,
    TriageRunResponse,
)
from app.services.case_engine import LiciCaseEngine
from app.services.decision_engine import LiciDecisionEngine
from app.services.memory_core_client import MemoryCoreClient
from app.services.radar_store import HybridRadarStore
from app.services.triage_store import HybridTriageStore


class LiciTriageEngine:
    def __init__(
        self,
        store: HybridTriageStore | None = None,
        radar_store: HybridRadarStore | None = None,
        memory: MemoryCoreClient | None = None,
        decision_engine: LiciDecisionEngine | None = None,
        case_engine: LiciCaseEngine | None = None,
    ):
        self.store = store or HybridTriageStore()
        self.radar_store = radar_store or HybridRadarStore()
        self.memory = memory or MemoryCoreClient()
        self.decision_engine = decision_engine or LiciDecisionEngine()
        self.case_engine = case_engine or LiciCaseEngine()

    def fila(self) -> TriageQueueResponse:
        itens = sorted(self.store.list_queue(), key=lambda i: (self._rank(i.classificacao), i.score_preliminar, i.atualizado_em), reverse=True)
        return TriageQueueResponse(total=len(itens), itens=itens)

    def logs(self) -> TriageLogsResponse:
        logs = sorted(self.store.list_logs(), key=lambda l: l.iniciado_em, reverse=True)
        return TriageLogsResponse(total=len(logs), logs=logs)

    def executar(self, request: TriageRunRequest | None = None) -> TriageRunResponse:
        request = request or TriageRunRequest()
        log = TriageRunLog()
        try:
            oportunidades = self.radar_store.list()
            pendentes = [o for o in oportunidades if request.incluir_oportunidade_com_caso or not o.caso_id][: request.limite]
            existentes = {item.oportunidade_id: item for item in self.store.list_queue()}
            fila: list[TriageItem] = []
            for oportunidade in pendentes:
                item = self._classificar(oportunidade)
                anterior = existentes.get(oportunidade.id)
                if anterior:
                    item.id = anterior.id
                    item.criado_em = anterior.criado_em
                    item.status = anterior.status
                    item.marcado_como = anterior.marcado_como
                    item.observacao = anterior.observacao
                fila.append(item)

            # preserva marcações de oportunidades que não entraram nesta execução
            ids_processados = {item.oportunidade_id for item in fila}
            for item in existentes.values():
                if item.oportunidade_id not in ids_processados and item.status != "pendente":
                    fila.append(item)

            self.store.write_queue(fila)
            log.status = "ok"
            log.finalizado_em = self._now()
            log.total_lidas = len(pendentes)
            log.total_classificadas = len([item for item in fila if item.oportunidade_id in ids_processados])
            log.prioridade_alta = sum(1 for item in fila if item.classificacao == "prioridade_alta")
            log.analisar = sum(1 for item in fila if item.classificacao == "analisar")
            log.monitorar = sum(1 for item in fila if item.classificacao == "monitorar")
            log.descartar = sum(1 for item in fila if item.classificacao == "descartar")
            self.store.append_log(log)
            return TriageRunResponse(log=log, fila=fila)
        except Exception as exc:
            log.status = "erro"
            log.finalizado_em = self._now()
            log.erro = str(exc)
            self.store.append_log(log)
            raise

    def marcar(self, opportunity_id: str, payload: TriageMarkRequest) -> TriageMarkResponse:
        item = self.store.get_item(opportunity_id)
        if item is None:
            oportunidade = self.radar_store.get(opportunity_id)
            if oportunidade is None:
                raise HTTPException(status_code=404, detail="oportunidade/triagem não encontrada")
            item = self._classificar(oportunidade)

        caso = None
        if payload.criar_caso:
            oportunidade = self.radar_store.get(item.oportunidade_id)
            if oportunidade is None:
                raise HTTPException(status_code=404, detail="oportunidade do Radar não encontrada")
            caso_record = self.case_engine.create_case(
                CaseCreate(
                    cliente=payload.cliente,
                    orgao=oportunidade.orgao or "Órgão não identificado",
                    objeto=oportunidade.objeto or "Objeto não identificado",
                    modalidade=oportunidade.modalidade,
                    fase_atual="prospecção",
                    score_estrategico=oportunidade.score_preliminar,
                    riscos=oportunidade.riscos_aparentes,
                    oportunidades=oportunidade.oportunidades_estrategicas,
                    memorias_relacionadas=oportunidade.memorias_relacionadas,
                    contexto=f"Caso criado a partir do LICI Triage Engine. Classificação: {item.classificacao}. Justificativa: {item.justificativa}",
                )
            )
            oportunidade.caso_id = caso_record.id
            oportunidade.atualizado_em = self._now()
            self.radar_store.update(oportunidade)
            item.status = "caso_criado"
            caso = caso_record.model_dump()
        elif payload.status:
            item.status = payload.status
        elif payload.marcado_como:
            item.status = "marcado"

        item.marcado_como = payload.marcado_como or item.marcado_como
        item.observacao = payload.observacao or item.observacao
        item.atualizado_em = self._now()
        item = self.store.update_item(item)
        return TriageMarkResponse(item=item, caso=caso)

    def _classificar(self, oportunidade: RadarOpportunity) -> TriageItem:
        memorias = oportunidade.memorias_relacionadas or self._buscar_memorias(oportunidade)
        score = oportunidade.score_preliminar
        risco_score = self._risco_score(oportunidade)
        valor = oportunidade.valor_estimado or 0
        prazo_score = oportunidade.criterios_score.get("prazo_disponivel", 45)
        aderencia = oportunidade.criterios_score.get("aderencia_segmento", 55)

        decisao = self.decision_engine.decidir(
            DecisionRequest(
                pergunta=f"Triagem automática: órgão {oportunidade.orgao}; objeto {oportunidade.objeto}; modalidade {oportunidade.modalidade}; valor {oportunidade.valor_estimado}; encerramento {oportunidade.data_encerramento}",
                termo_memoria=f"{oportunidade.orgao} {oportunidade.objeto}",
                criterios=DecisionCriteria(
                    aderencia_tecnica=aderencia,
                    risco_habilitacao=45 if aderencia >= 60 else 65,
                    risco_juridico=risco_score,
                    oportunidade_competitiva=oportunidade.criterios_score.get("oportunidade_estrategica", 55),
                    risco_execucao=risco_score,
                    historico_memoria_viva=min(100, 45 + len(memorias) * 10),
                    necessidade_impugnacao=25,
                    chance_estrategica_vitoria=score,
                ),
                consultar_rag=False,
            )
        )

        if score >= 70 and risco_score < 75 and prazo_score >= 45:
            classificacao = "prioridade_alta"
        elif score >= 55 or decisao.decisao in {"PARTICIPAR", "ESTRATÉGIA HÍBRIDA"}:
            classificacao = "analisar"
        elif score >= 40 and risco_score < 80:
            classificacao = "monitorar"
        else:
            classificacao = "descartar"

        risco_aparente = self._risco_aparente(oportunidade, risco_score, prazo_score)
        oportunidade_estrategica = self._oportunidade_estrategica(oportunidade, memorias, valor, aderencia)
        justificativa = self._justificativa(oportunidade, classificacao, decisao.decisao, risco_aparente, oportunidade_estrategica)
        memoria = self._memoria_sugerida(oportunidade, classificacao, justificativa) if classificacao == "prioridade_alta" or memorias else None

        return TriageItem(
            oportunidade_id=oportunidade.id,
            pncp_id=oportunidade.pncp_id,
            orgao=oportunidade.orgao,
            uf=oportunidade.uf,
            objeto=oportunidade.objeto,
            modalidade=oportunidade.modalidade,
            valor_estimado=oportunidade.valor_estimado,
            data_encerramento=oportunidade.data_encerramento,
            score_preliminar=oportunidade.score_preliminar,
            classificacao=classificacao,
            justificativa=justificativa,
            risco_aparente=risco_aparente,
            oportunidade_estrategica=oportunidade_estrategica,
            sugerir_criacao_caso=classificacao == "prioridade_alta",
            acao_recomendada=self._acao_recomendada(classificacao),
            memoria_sugerida=memoria,
            oportunidade=oportunidade,
        )

    def _buscar_memorias(self, oportunidade: RadarOpportunity) -> list[dict]:
        resultados: list[dict] = []
        for termo in [oportunidade.orgao, oportunidade.objeto[:80]]:
            if not termo:
                continue
            memoria = self.memory.buscar(termo)
            resultados.extend(memoria.get("resultados", []))
        return resultados

    def _risco_score(self, oportunidade: RadarOpportunity) -> int:
        risco = oportunidade.criterios_score.get("risco_aparente", 45)
        texto = f"{oportunidade.objeto} {oportunidade.modalidade}".casefold()
        if any(t in texto for t in ["adesão", "adesao", "emergencial", "obra", "engenharia", "dedicação exclusiva"]):
            risco += 15
        if oportunidade.valor_estimado is None or oportunidade.valor_estimado == 0:
            risco += 10
        return max(0, min(100, risco))

    def _risco_aparente(self, oportunidade: RadarOpportunity, risco_score: int, prazo_score: int) -> str:
        riscos = list(oportunidade.riscos_aparentes)
        if prazo_score < 45:
            riscos.append("Prazo crítico ou encerrado; alta chance de perda operacional se não houver preparação imediata.")
        if risco_score >= 70:
            riscos.append("Objeto/modalidade sugere risco elevado de execução, qualificação técnica ou aderência documental.")
        if oportunidade.valor_estimado is None or oportunidade.valor_estimado == 0:
            riscos.append("Valor estimado ausente ou zerado no PNCP; validar anexos antes de priorizar.")
        return " ".join(dict.fromkeys(riscos)) or "Risco aparente baixo/moderado; confirmar edital antes de decisão final."

    def _oportunidade_estrategica(self, oportunidade: RadarOpportunity, memorias: list[dict], valor: float, aderencia: int) -> str:
        pontos = list(oportunidade.oportunidades_estrategicas)
        if aderencia >= 70:
            pontos.append("Alta aderência preliminar às palavras-chave/segmento monitorado.")
        if valor >= 250_000:
            pontos.append("Valor estimado relevante para priorização comercial.")
        if memorias:
            pontos.append("Há memória relacionada ao órgão/objeto; usar histórico para calibrar ataque e blindagem documental.")
        return " ".join(dict.fromkeys(pontos)) or "Oportunidade ainda fraca; monitorar até confirmar aderência técnica, margem e prazo."

    def _justificativa(self, oportunidade: RadarOpportunity, classificacao: str, decisao: str, risco: str, oportunidade_txt: str) -> str:
        return (
            f"Classificação {classificacao} com score Radar {oportunidade.score_preliminar}/100 e decisão auxiliar {decisao}. "
            f"Risco: {risco} Oportunidade: {oportunidade_txt}"
        )

    def _acao_recomendada(self, classificacao: str) -> str:
        return {
            "prioridade_alta": "Submeter à atenção humana e criar caso vivo se houver aderência comercial mínima.",
            "analisar": "Ler edital/anexos e validar habilitação, margem, prazo e risco antes de criar caso.",
            "monitorar": "Manter na fila; reavaliar se surgir memória, retificação, prazo melhor ou aderência clara.",
            "descartar": "Não alocar esforço agora; manter registro apenas para histórico e inteligência futura.",
        }[classificacao]

    def _memoria_sugerida(self, oportunidade: RadarOpportunity, classificacao: str, justificativa: str) -> MemorySuggestion:
        return MemorySuggestion(
            tipo="padrao" if classificacao != "descartar" else "risco",
            titulo=f"Triagem Radar: {classificacao} - {oportunidade.orgao}",
            descricao=f"Triagem automática classificou oportunidade PNCP {oportunidade.pncp_id}: {oportunidade.objeto[:180]}",
            estrategia=self._acao_recomendada(classificacao),
            aprendizado=justificativa,
            uso_futuro="Reutilizar classificação para calibrar Radar, Scheduler, decisão de caso vivo e atenção humana.",
            tags=["triage-engine", "radar", classificacao, oportunidade.uf, oportunidade.orgao],
        )

    def _rank(self, classificacao: str) -> int:
        return {"prioridade_alta": 4, "analisar": 3, "monitorar": 2, "descartar": 1}.get(classificacao, 0)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
