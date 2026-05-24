from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.schemas.radar import RadarOpportunity, RadarSearchRequest
from app.schemas.scheduler import (
    SchedulerConfig,
    SchedulerLogsResponse,
    SchedulerRunLog,
    SchedulerRunRequest,
    SchedulerRunResponse,
    SchedulerStatusResponse,
)
from app.services.audit_log import audit_event
from app.services.radar_engine import LiciRadarEngine
from app.services.radar_store import HybridRadarStore
from app.services.scheduler_store import JsonSchedulerStore


class LiciScheduler:
    def __init__(
        self,
        store: JsonSchedulerStore | None = None,
        radar_engine: LiciRadarEngine | None = None,
        radar_store: HybridRadarStore | None = None,
    ):
        self.store = store or JsonSchedulerStore()
        self.radar_store = radar_store or HybridRadarStore()
        self.radar_engine = radar_engine or LiciRadarEngine(store=self.radar_store)

    def status(self) -> SchedulerStatusResponse:
        config = self.store.read_config()
        oportunidades = self.radar_store.list()
        fila = self._fila_triagem(oportunidades)
        logs = self.store.list_logs()
        ultimo = sorted(logs, key=lambda l: l.iniciado_em, reverse=True)[0] if logs else None
        return SchedulerStatusResponse(
            config=config,
            total_oportunidades_salvas=len(oportunidades),
            fila_triagem_total=len(fila),
            fila_triagem=fila,
            ultimo_log=ultimo,
        )

    def logs(self) -> SchedulerLogsResponse:
        logs = sorted(self.store.list_logs(), key=lambda l: l.iniciado_em, reverse=True)
        return SchedulerLogsResponse(total=len(logs), logs=logs)

    def executar_radar(self, request: SchedulerRunRequest | None = None) -> SchedulerRunResponse:
        request = request or SchedulerRunRequest()
        config = request.sobrescrever_config or self.store.read_config()
        if request.limite is not None:
            config = config.model_copy(update={"limite": request.limite})
        if request.sobrescrever_config and request.salvar_config:
            self.store.write_config(config)

        antes = self.radar_store.list()
        chaves_antes = {self._opportunity_key(item) for item in antes}
        payload = self._radar_payload(config)
        log = SchedulerRunLog(config_usada=config, radar_payload=payload.model_dump(mode="json"))

        try:
            resultado = self.radar_engine.buscar(payload)
            depois = self.radar_store.list()
            chaves_depois = {self._opportunity_key(item) for item in depois}
            novas_chaves = chaves_depois - chaves_antes
            oportunidades_retornadas = resultado.oportunidades
            duplicadas = max(0, len(oportunidades_retornadas) - len(novas_chaves))
            fila = self._fila_triagem(depois)

            log.status = "ok"
            log.finalizado_em = self._now()
            log.total_encontradas = resultado.total
            log.novas_oportunidades = len(novas_chaves)
            log.duplicadas_evitas = duplicadas
            log.fila_triagem_total = len(fila)
            log.fila_triagem = fila
            log.aviso = resultado.aviso
            self.store.append_log(log)
            audit_event(
                modulo="scheduler",
                acao="execucao_scheduler",
                status="ok",
                detalhes={
                    "total_encontradas": log.total_encontradas,
                    "novas_oportunidades": log.novas_oportunidades,
                    "duplicadas_evitas": log.duplicadas_evitas,
                    "fila_triagem_total": log.fila_triagem_total,
                    "aviso": log.aviso,
                },
                id_relacionado=log.id,
            )
            return SchedulerRunResponse(log=log, oportunidades=oportunidades_retornadas)
        except Exception as exc:
            log.status = "erro"
            log.finalizado_em = self._now()
            log.erro = str(exc)
            log.fila_triagem = self._fila_triagem(self.radar_store.list())
            log.fila_triagem_total = len(log.fila_triagem)
            self.store.append_log(log)
            audit_event(
                modulo="scheduler",
                acao="execucao_scheduler",
                status="erro",
                detalhes={"erro": str(exc), "fila_triagem_total": log.fila_triagem_total},
                id_relacionado=log.id,
            )
            raise

    def _radar_payload(self, config: SchedulerConfig) -> RadarSearchRequest:
        hoje = date.today()
        return RadarSearchRequest(
            uf=config.uf,
            palavras_chave=config.palavras_chave,
            data_inicial=hoje - timedelta(days=config.dias_busca),
            data_final=hoje,
            limite=config.limite,
            cliente=config.cliente_padrao,
            salvar=True,
        )

    def _fila_triagem(self, oportunidades: list[RadarOpportunity]) -> list[dict[str, Any]]:
        pendentes = [item for item in oportunidades if not item.caso_id]
        pendentes = sorted(pendentes, key=lambda o: (o.score_preliminar, o.atualizado_em), reverse=True)
        fila: list[dict[str, Any]] = []
        for item in pendentes:
            fila.append(
                {
                    "id": item.id,
                    "pncp_id": item.pncp_id,
                    "orgao": item.orgao,
                    "uf": item.uf,
                    "objeto": item.objeto,
                    "modalidade": item.modalidade,
                    "valor_estimado": item.valor_estimado,
                    "data_publicacao": item.data_publicacao,
                    "data_encerramento": item.data_encerramento,
                    "score_preliminar": item.score_preliminar,
                    "riscos_aparentes": item.riscos_aparentes,
                    "acao_recomendada": self._acao_triagem(item),
                }
            )
        return fila

    def _acao_triagem(self, oportunidade: RadarOpportunity) -> str:
        if oportunidade.score_preliminar >= 70:
            return "Prioridade alta: ler edital/anexos e avaliar criação imediata de caso vivo."
        if oportunidade.score_preliminar >= 50:
            return "Prioridade média: validar aderência, valor, prazo e documentação antes de criar caso."
        return "Prioridade baixa: manter em observação; criar caso apenas se houver aderência comercial clara."

    def _opportunity_key(self, opportunity: RadarOpportunity) -> str:
        return opportunity.pncp_id or f"{opportunity.orgao}|{opportunity.objeto}|{opportunity.data_publicacao}|{opportunity.valor_estimado}"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
