from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.schemas.case import (
    CaseCreate,
    CaseEvent,
    CaseEventCreate,
    CaseListResponse,
    CasePhaseUpdate,
    CaseRecord,
    CaseTimelineResponse,
    CaseUpdate,
)
from app.schemas.decision import DecisionCriteria, DecisionRequest, DecisionResponse, MemorySuggestion
from app.schemas.edital import EditalAnalyzeTextRequest
from app.services.audit_log import audit_event
from app.services.case_store import HybridCaseStore, JsonCaseStore
from app.services.decision_engine import LiciDecisionEngine
from app.services.edital_analyzer import LiciEditalAnalyzer
from app.services.memory_core_client import MemoryCoreClient
from app.services.rag_client import RagClient


class LiciCaseEngine:
    def __init__(
        self,
        store: JsonCaseStore | None = None,
        memory: MemoryCoreClient | None = None,
        decision_engine: LiciDecisionEngine | None = None,
        edital_analyzer: LiciEditalAnalyzer | None = None,
        rag_client: RagClient | None = None,
    ):
        self.store = store or HybridCaseStore()
        self.memory = memory or MemoryCoreClient()
        self.decision_engine = decision_engine or LiciDecisionEngine()
        self.edital_analyzer = edital_analyzer or LiciEditalAnalyzer()
        self.rag_client = rag_client or RagClient()

    def list_cases(self, organization_id: str | None = None) -> CaseListResponse:
        casos = self.store.list(organization_id=organization_id)
        return CaseListResponse(total=len(casos), casos=casos)

    def create_case(self, payload: CaseCreate, organization_id: str | None = None) -> CaseRecord:
        if organization_id and not payload.organization_id:
            payload = payload.model_copy(update={"organization_id": organization_id})
        memorias = list(payload.memorias_relacionadas)
        memorias.extend(self._buscar_memorias_relacionadas(payload.orgao, payload.objeto))
        memorias = self._dedupe_memorias(memorias)

        riscos = list(payload.riscos)
        oportunidades = list(payload.oportunidades)
        score = payload.score_estrategico
        memoria_sugerida: MemorySuggestion | None = None

        if payload.texto_edital:
            edital = self.edital_analyzer.analisar_texto(
                EditalAnalyzeTextRequest(
                    texto=payload.texto_edital,
                    termo_memoria=f"{payload.orgao} {payload.objeto}",
                    contexto_usuario=payload.contexto,
                    consultar_rag=False,
                )
            )
            riscos = self._merge_texts(riscos, edital.riscos)
            oportunidades = self._merge_texts(oportunidades, edital.oportunidades)
            score = edital.decisao_recomendada.score
            memoria_sugerida = edital.memoria_sugerida
        else:
            decisao = self.decision_engine.decidir(
                DecisionRequest(
                    pergunta=f"Caso licitatório: órgão {payload.orgao}; objeto {payload.objeto}; modalidade {payload.modalidade}; contexto {payload.contexto}",
                    termo_memoria=f"{payload.orgao} {payload.objeto}",
                    criterios=DecisionCriteria(
                        historico_memoria_viva=min(100, 45 + len(memorias) * 10),
                        oportunidade_competitiva=65 if oportunidades else None,
                    ),
                    consultar_rag=False,
                )
            )
            score = decisao.score
            riscos = self._merge_texts(riscos, decisao.riscos_criticos)
            oportunidades = oportunidades or ["Avaliar oportunidade competitiva com base no edital, margem e aderência documental."]
            memoria_sugerida = decisao.memoria_sugerida

        evento_inicial = CaseEvent(
            tipo="edital analisado" if payload.texto_edital else "caso criado",
            fase=payload.fase_atual,
            descricao="Caso operacional criado no LICI Case Engine.",
            impacto="Início do acompanhamento operacional vivo da licitação.",
            aprendizado_operacional="Toda licitação relevante deve possuir histórico, timeline, decisão e memória reutilizável.",
            memoria_sugerida=memoria_sugerida,
        )

        case = CaseRecord(
            **payload.model_dump(exclude={"memorias_relacionadas", "riscos", "oportunidades", "score_estrategico"}),
            score_estrategico=score,
            riscos=riscos,
            oportunidades=oportunidades,
            memorias_relacionadas=memorias,
            historico_operacional=[evento_inicial],
            memoria_sugerida=memoria_sugerida,
        )
        created = self.store.create(case)
        audit_event(
            modulo="case_engine",
            acao="criacao_caso",
            status="ok",
            detalhes={"orgao": created.orgao, "objeto": created.objeto, "fase": created.fase_atual, "score": created.score_estrategico},
            id_relacionado=created.id,
        )
        return created

    def get_case(self, case_id: str, organization_id: str | None = None) -> CaseRecord:
        case = self.store.get(case_id, organization_id=organization_id)
        if case is None:
            if organization_id and self.store.get(case_id) is not None:
                audit_event("security", "acesso_negado_cross_org", "erro", {"recurso": "caso", "case_id": case_id, "organization_id": organization_id}, case_id)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: caso pertence a outra organização")
            raise HTTPException(status_code=404, detail="caso não encontrado")
        return case


    def update_case(self, case_id: str, payload: CaseUpdate, organization_id: str | None = None) -> CaseRecord:
        case = self.get_case(case_id, organization_id=organization_id)
        changes = payload.model_dump(exclude_unset=True)
        before_phase = case.fase_atual
        for key, value in changes.items():
            if value is not None:
                setattr(case, key, value)
        case.atualizado_em = self._now()
        if changes:
            event = CaseEvent(
                tipo="caso atualizado",
                fase=case.fase_atual,
                descricao="Dados operacionais do caso atualizados.",
                impacto="Cadastro, riscos, oportunidades ou status foram revisados para apoiar a execução.",
                aprendizado_operacional="Manter caso vivo atualizado reduz risco de perda operacional e decisão com dado defasado.",
            )
            if before_phase != case.fase_atual:
                event.descricao = f"Caso atualizado e fase alterada: {before_phase} → {case.fase_atual}."
            case.historico_operacional.append(event)
        updated = self.store.update(case)
        audit_event(
            modulo="case_engine",
            acao="atualizacao_caso",
            status="ok",
            detalhes={"campos": sorted(changes.keys()), "fase": updated.fase_atual, "status_caso": updated.status},
            id_relacionado=updated.id,
        )
        return updated

    def archive_case(self, case_id: str, organization_id: str | None = None) -> CaseRecord:
        case = self.get_case(case_id, organization_id=organization_id)
        case.status = "arquivado"
        case.atualizado_em = self._now()
        case.historico_operacional.append(
            CaseEvent(
                tipo="caso arquivado",
                fase=case.fase_atual,
                descricao="Caso arquivado operacionalmente.",
                impacto="Sai da mesa ativa, mas permanece consultável para histórico, relatório e aprendizado.",
                aprendizado_operacional="Arquivar casos encerrados ou sem ação limpa a operação sem apagar memória.",
            )
        )
        updated = self.store.update(case)
        audit_event("case_engine", "arquivamento_caso", "ok", {"status_caso": updated.status}, updated.id)
        return updated

    def update_phase(self, case_id: str, payload: CasePhaseUpdate, organization_id: str | None = None) -> CaseRecord:
        case = self.get_case(case_id, organization_id=organization_id)
        case.fase_atual = payload.fase_atual
        if payload.status:
            case.status = payload.status
        case.atualizado_em = self._now()

        memoria = self._memoria_sugerida_fase(case, payload)
        event = CaseEvent(
            tipo="fase atualizada",
            fase=payload.fase_atual,
            descricao=payload.descricao or f"Fase atualizada para {payload.fase_atual}.",
            impacto=f"Caso passou para a fase {payload.fase_atual}.",
            aprendizado_operacional=payload.aprendizado_operacional,
            memoria_sugerida=memoria,
        )
        case.historico_operacional.append(event)
        case.memoria_sugerida = memoria
        case.score_estrategico = self._recalcular_score(case)
        updated = self.store.update(case)
        audit_event(
            modulo="case_engine",
            acao="mudanca_fase",
            status="ok",
            detalhes={"fase": updated.fase_atual, "status_caso": updated.status, "score": updated.score_estrategico},
            id_relacionado=updated.id,
        )
        return updated

    def register_event(self, case_id: str, payload: CaseEventCreate, organization_id: str | None = None) -> CaseRecord:
        case = self.get_case(case_id, organization_id=organization_id)
        memoria = self._memoria_sugerida_evento(case, payload) if payload.gerar_memoria_sugerida else None
        event = CaseEvent(
            tipo=payload.tipo,
            fase=case.fase_atual,
            descricao=payload.descricao,
            impacto=payload.impacto,
            aprendizado_operacional=payload.aprendizado_operacional,
            memoria_sugerida=memoria,
        )
        case.historico_operacional.append(event)
        case.atualizado_em = self._now()
        case.memoria_sugerida = memoria or case.memoria_sugerida
        self._aplicar_evento_no_status(case, payload.tipo)
        case.score_estrategico = self._recalcular_score(case)
        updated = self.store.update(case)
        audit_event(
            modulo="case_engine",
            acao="registro_evento",
            status="ok",
            detalhes={"tipo": payload.tipo, "fase": updated.fase_atual, "status_caso": updated.status, "score": updated.score_estrategico},
            id_relacionado=updated.id,
        )
        return updated

    def register_decision_consequence(
        self,
        payload: DecisionRequest,
        decisao: DecisionResponse,
        organization_id: str | None = None,
    ) -> dict:
        event_payload = CaseEventCreate(
            tipo="decisão operacional",
            descricao=f"Decision Engine gerou {decisao.decisao} com score {decisao.score}/100.",
            impacto=decisao.acao_imediata,
            aprendizado_operacional=(
                "Decisão supervisionada deve gerar consequência persistente no caso: timeline, audit log "
                "e próximo movimento operacional rastreável."
            ),
            gerar_memoria_sugerida=True,
        )

        if payload.caso_id:
            updated = self.register_event(payload.caso_id, event_payload, organization_id=organization_id)
            event = updated.historico_operacional[-1] if updated.historico_operacional else None
            audit_event(
                modulo="decision_engine",
                acao="consequencia_operacional_registrada",
                status="ok",
                detalhes={"modo": "timeline", "decisao": decisao.decisao, "score": decisao.score},
                id_relacionado=updated.id,
            )
            return {
                "registrada": True,
                "modo": "timeline",
                "caso_id": updated.id,
                "evento_id": event.id if event else None,
                "fase_atual": updated.fase_atual,
                "status_caso": updated.status,
            }

        created = self.create_case(
            CaseCreate(
                organization_id=organization_id,
                cliente=payload.cliente_id or "Cliente não informado",
                orgao="Órgão a identificar",
                objeto=self._titulo_caso_decisao(payload, decisao),
                modalidade="",
                fase_atual="análise",
                score_estrategico=decisao.score,
                riscos=decisao.riscos_criticos,
                oportunidades=self._oportunidades_decisao(decisao),
                contexto=self._contexto_decisao(payload, decisao),
            ),
            organization_id=organization_id,
        )
        updated = self.register_event(created.id, event_payload, organization_id=organization_id)
        event = updated.historico_operacional[-1] if updated.historico_operacional else None
        audit_event(
            modulo="decision_engine",
            acao="consequencia_operacional_registrada",
            status="ok",
            detalhes={"modo": "caso_criado", "decisao": decisao.decisao, "score": decisao.score},
            id_relacionado=updated.id,
        )
        return {
            "registrada": True,
            "modo": "caso_criado",
            "caso_id": updated.id,
            "evento_id": event.id if event else None,
            "fase_atual": updated.fase_atual,
            "status_caso": updated.status,
        }

    def timeline(self, case_id: str, organization_id: str | None = None) -> CaseTimelineResponse:
        case = self.get_case(case_id, organization_id=organization_id)
        timeline = sorted(case.historico_operacional, key=lambda e: e.data)
        return CaseTimelineResponse(caso_id=case_id, total=len(timeline), timeline=timeline)

    def _titulo_caso_decisao(self, payload: DecisionRequest, decisao: DecisionResponse) -> str:
        titulo = payload.titulo_caso or decisao.termo_memoria or payload.pergunta
        titulo = " ".join(titulo.split())
        return titulo[:180] if len(titulo) > 180 else titulo

    def _oportunidades_decisao(self, decisao: DecisionResponse) -> list[str]:
        oportunidades = []
        if decisao.oportunidade_ataque:
            oportunidades.append(decisao.oportunidade_ataque)
        if decisao.recomendacao_blindagem:
            oportunidades.append(decisao.recomendacao_blindagem)
        return oportunidades or ["Executar próxima ação recomendada pelo Decision Engine."]

    def _contexto_decisao(self, payload: DecisionRequest, decisao: DecisionResponse) -> str:
        partes = [
            f"Pergunta original: {payload.pergunta}",
            f"Decisão: {decisao.decisao}",
            f"Score: {decisao.score}/100",
            f"Ação imediata: {decisao.acao_imediata}",
        ]
        if payload.contexto:
            partes.append(f"Contexto informado: {payload.contexto}")
        return "\n".join(partes)

    def _buscar_memorias_relacionadas(self, orgao: str, objeto: str) -> list[dict]:
        resultados: list[dict] = []
        for termo in [orgao, objeto]:
            if not termo:
                continue
            memoria = self.memory.buscar(termo)
            resultados.extend(memoria.get("resultados", []))
        return resultados

    def _dedupe_memorias(self, memorias: list[dict]) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for memoria in memorias:
            key = memoria.get("id") or repr(memoria)
            if key in seen:
                continue
            seen.add(key)
            out.append(memoria)
        return out

    def _merge_texts(self, left: list[str], right: list[str]) -> list[str]:
        seen = set()
        out = []
        for item in left + right:
            if item and item not in seen:
                seen.add(item)
                out.append(item)
        return out

    def _memoria_sugerida_fase(self, case: CaseRecord, payload: CasePhaseUpdate) -> MemorySuggestion:
        return MemorySuggestion(
            tipo="padrao" if payload.fase_atual not in {"encerrado"} else "contrato",
            titulo=f"Caso {case.id}: fase {payload.fase_atual}",
            descricao=f"Caso do órgão {case.orgao} para objeto {case.objeto} avançou para {payload.fase_atual}.",
            estrategia=payload.descricao or f"Executar ações operacionais da fase {payload.fase_atual}.",
            aprendizado=payload.aprendizado_operacional or "Mudança de fase deve atualizar timeline, risco, oportunidade e próximos movimentos.",
            uso_futuro="Comparar evolução de fase com casos futuros do mesmo órgão/objeto.",
            tags=["case-engine", "fase", str(payload.fase_atual), case.orgao],
        )

    def _memoria_sugerida_evento(self, case: CaseRecord, payload: CaseEventCreate) -> MemorySuggestion:
        tipo = "vitoria" if payload.tipo == "vitória" else "perda" if payload.tipo == "perda" else "padrao"
        if payload.tipo in {"pagamento atrasado", "reequilíbrio solicitado"}:
            tipo = "contrato"
        return MemorySuggestion(
            tipo=tipo,
            titulo=f"Caso {case.id}: {payload.tipo}",
            descricao=payload.descricao,
            estrategia=payload.impacto or "Usar evento para ajustar estratégia operacional do caso.",
            aprendizado=payload.aprendizado_operacional or "Evento operacional registrado para alimentar histórico vivo e aprendizado futuro.",
            uso_futuro="Reutilizar como histórico operacional em casos semelhantes, órgãos recorrentes e estratégias futuras.",
            tags=["case-engine", str(payload.tipo), case.fase_atual, case.orgao],
        )

    def _aplicar_evento_no_status(self, case: CaseRecord, tipo: str) -> None:
        if tipo == "vitória":
            case.status = "vencido"
            case.fase_atual = "homologação"
        elif tipo == "perda":
            case.status = "perdido"
            case.fase_atual = "encerrado"
        elif tipo == "contrato assinado":
            case.fase_atual = "contrato"
        elif tipo == "pagamento atrasado":
            case.fase_atual = "pagamento"
        elif tipo == "reequilíbrio solicitado":
            case.fase_atual = "execução"

    def _recalcular_score(self, case: CaseRecord) -> int:
        score = case.score_estrategico
        if case.status == "vencido":
            score = max(score, 90)
        elif case.status == "perdido":
            score = min(score, 20)
        elif case.fase_atual in {"disputa", "homologação", "contrato"}:
            score = min(100, score + 5)
        if any("inabilitação" in risco.casefold() for risco in case.riscos):
            score = max(0, score - 3)
        return max(0, min(100, score))

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
