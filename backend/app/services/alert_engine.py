from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import HTTPException

from app.schemas.alert import (
    AlertGenerateLog,
    AlertGenerateRequest,
    AlertGenerateResponse,
    AlertListResponse,
    AlertLogsResponse,
    AlertMarkReadResponse,
    AlertRecord,
    AlertSeverity,
)
from app.schemas.case import CaseRecord
from app.schemas.triage import TriageItem
from app.services.audit_log import audit_event
from app.services.alert_store import HybridAlertStore
from app.services.case_store import JsonCaseStore
from app.services.memory_core_client import MemoryCoreClient
from app.services.radar_store import HybridRadarStore
from app.services.triage_store import HybridTriageStore


class LiciAlertEngine:
    def __init__(
        self,
        store: HybridAlertStore | None = None,
        triage_store: HybridTriageStore | None = None,
        radar_store: HybridRadarStore | None = None,
        case_store: JsonCaseStore | None = None,
        memory: MemoryCoreClient | None = None,
    ):
        self.store = store or HybridAlertStore()
        self.triage_store = triage_store or HybridTriageStore()
        self.radar_store = radar_store or HybridRadarStore()
        self.case_store = case_store or JsonCaseStore()
        self.memory = memory or MemoryCoreClient()

    def list_alerts(self, incluir_lidos: bool = True) -> AlertListResponse:
        alerts = self.store.list_alerts()
        if not incluir_lidos:
            alerts = [item for item in alerts if not item.lido]
        alerts = sorted(alerts, key=lambda a: (self._severity_rank(a.severidade), a.criado_em), reverse=True)
        return AlertListResponse(total=len(alerts), nao_lidos=sum(1 for a in alerts if not a.lido), alertas=alerts)

    def logs(self) -> AlertLogsResponse:
        logs = sorted(self.store.list_logs(), key=lambda l: l.iniciado_em, reverse=True)
        return AlertLogsResponse(total=len(logs), logs=logs)

    def gerar(self, request: AlertGenerateRequest | None = None) -> AlertGenerateResponse:
        request = request or AlertGenerateRequest()
        log = AlertGenerateLog()
        try:
            triagem = self.triage_store.list_queue()[: request.limite_triagem]
            casos = self.case_store.list()[: request.limite_casos]
            alerts: list[AlertRecord] = []
            alerts.extend(self._alertas_triagem(triagem))
            alerts.extend(self._alertas_prazos(triagem))
            alerts.extend(self._alertas_casos(casos))
            saved, novos, atualizados = self.store.upsert_many(alerts)
            if not request.incluir_lidos:
                saved = [a for a in saved if not a.lido]

            log.status = "ok"
            log.finalizado_em = self._now()
            log.total_gerados = len(alerts)
            log.novos = novos
            log.atualizados = atualizados
            log.critica = sum(1 for a in alerts if a.severidade == "critica")
            log.alta = sum(1 for a in alerts if a.severidade == "alta")
            log.media = sum(1 for a in alerts if a.severidade == "media")
            log.baixa = sum(1 for a in alerts if a.severidade == "baixa")
            self.store.append_log(log)
            audit_event(
                modulo="alert_engine",
                acao="criacao_alerta",
                status="ok",
                detalhes={
                    "total_gerados": log.total_gerados,
                    "novos": log.novos,
                    "atualizados": log.atualizados,
                    "critica": log.critica,
                    "alta": log.alta,
                },
                id_relacionado=log.id,
            )
            return AlertGenerateResponse(log=log, alertas=saved)
        except Exception as exc:
            log.status = "erro"
            log.finalizado_em = self._now()
            log.erro = str(exc)
            self.store.append_log(log)
            audit_event(
                modulo="alert_engine",
                acao="criacao_alerta",
                status="erro",
                detalhes={"erro": str(exc)},
                id_relacionado=log.id,
            )
            raise

    def arquivar(self, alert_id: str) -> AlertMarkReadResponse:
        alert = self.store.get(alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail='alerta não encontrado')
        alert.lido = True
        alert.metadata = {**(alert.metadata or {}), 'arquivado': True, 'arquivado_em': self._now()}
        alert.atualizado_em = self._now()
        alert = self.store.update(alert)
        audit_event('alert_engine', 'arquivamento_alerta', 'ok', {'titulo': alert.titulo, 'severidade': alert.severidade}, alert.id)
        return AlertMarkReadResponse(alerta=alert)

    def marcar_lido(self, alert_id: str) -> AlertMarkReadResponse:
        alert = self.store.get(alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="alerta não encontrado")
        alert.lido = True
        alert.atualizado_em = self._now()
        alert = self.store.update(alert)
        audit_event(
            modulo="alert_engine",
            acao="marcacao_alerta_lido",
            status="ok",
            detalhes={"titulo": alert.titulo, "severidade": alert.severidade, "referencia_id": alert.referencia_id},
            id_relacionado=alert.id,
        )
        return AlertMarkReadResponse(alerta=alert)

    def _alertas_triagem(self, items: list[TriageItem]) -> list[AlertRecord]:
        alerts: list[AlertRecord] = []
        for item in items:
            if item.status != "pendente":
                continue
            if item.classificacao == "prioridade_alta":
                alerts.append(
                    AlertRecord(
                        chave=f"triagem:prioridade_alta:{item.oportunidade_id}",
                        titulo=f"Prioridade alta na triagem: {item.orgao}",
                        mensagem=f"Oportunidade classificada como prioridade_alta com score {item.score_preliminar}/100.",
                        severidade="alta" if item.score_preliminar < 80 else "critica",
                        fonte="triagem",
                        referencia_id=item.oportunidade_id,
                        orgao=item.orgao,
                        objeto=item.objeto,
                        risco=item.risco_aparente,
                        oportunidade=item.oportunidade_estrategica,
                        acao_recomendada="Atenção humana imediata: ler edital/anexos e decidir criação de caso vivo.",
                        metadata={"triagem_id": item.id, "classificacao": item.classificacao},
                    )
                )
        return alerts

    def _alertas_prazos(self, items: list[TriageItem]) -> list[AlertRecord]:
        alerts: list[AlertRecord] = []
        for item in items:
            if item.status != "pendente":
                continue
            dias = self._dias_ate(item.data_encerramento)
            if dias is None or dias > 5:
                continue
            if dias < 0:
                severidade: AlertSeverity = "media"
                msg = "Prazo de encerramento aparentemente já passou; validar se ainda há janela útil ou descartar."
            elif dias <= 1:
                severidade = "critica"
                msg = "Prazo crítico: encerramento em até 24h."
            elif dias <= 3:
                severidade = "alta"
                msg = f"Prazo apertado: encerramento em {dias} dias."
            else:
                severidade = "media"
                msg = f"Prazo próximo: encerramento em {dias} dias."
            alerts.append(
                AlertRecord(
                    chave=f"triagem:prazo:{item.oportunidade_id}",
                    titulo=f"Prazo crítico/próximo: {item.orgao}",
                    mensagem=msg,
                    severidade=severidade,
                    fonte="radar",
                    referencia_id=item.oportunidade_id,
                    orgao=item.orgao,
                    objeto=item.objeto,
                    risco=item.risco_aparente,
                    oportunidade=item.oportunidade_estrategica,
                    acao_recomendada="Validar imediatamente data da sessão, documentos e viabilidade de proposta.",
                    metadata={"triagem_id": item.id, "data_encerramento": item.data_encerramento, "dias_ate_encerramento": dias},
                )
            )
        return alerts

    def _alertas_casos(self, casos: list[CaseRecord]) -> list[AlertRecord]:
        alerts: list[AlertRecord] = []
        for case in casos:
            if case.status not in {"ativo", "suspenso"}:
                continue
            alerta = self._alerta_caso(case)
            if alerta:
                alerts.append(alerta)
        return alerts

    def _alerta_caso(self, case: CaseRecord) -> AlertRecord | None:
        fase = case.fase_atual
        riscos_texto = " ".join(case.riscos).casefold()
        memorias = self.memory.buscar(case.orgao).get("resultados", []) if case.orgao else []
        if fase in {"prospecção", "análise"}:
            severidade: AlertSeverity = "alta" if case.score_estrategico >= 70 else "media"
            acao = "Definir decisão operacional: participar, impugnar, criar checklist ou descartar."
            titulo = f"Caso vivo exige decisão: {case.orgao}"
        elif fase == "impugnação":
            severidade = "critica"
            acao = "Preparar/protocolar impugnação e controlar prazo de resposta e eventual reabertura."
            titulo = f"Impugnação pendente: {case.orgao}"
        elif fase in {"habilitação", "disputa", "recurso"}:
            severidade = "alta"
            acao = "Checar documentos, proposta, sessão, intenção de recurso e falhas de concorrentes."
            titulo = f"Ação operacional na fase {fase}: {case.orgao}"
        elif "inabilitação" in riscos_texto or "prazo" in riscos_texto or "pagamento atrasado" in riscos_texto:
            severidade = "alta"
            acao = "Atuar sobre risco crítico registrado no caso antes que gere perda/desclassificação."
            titulo = f"Risco crítico em caso vivo: {case.orgao}"
        else:
            return None

        if memorias and severidade == "media":
            severidade = "alta"

        return AlertRecord(
            chave=f"case:acao:{case.id}:{case.fase_atual}",
            titulo=titulo,
            mensagem=f"Caso {case.id} está na fase {case.fase_atual}, status {case.status}, score {case.score_estrategico}/100.",
            severidade=severidade,
            fonte="case",
            referencia_id=case.id,
            orgao=case.orgao,
            objeto=case.objeto,
            risco="; ".join(case.riscos) or "Caso ativo sem risco detalhado; revisar próximos movimentos.",
            oportunidade="; ".join(case.oportunidades) or "Caso vivo pode gerar vantagem se houver ação tempestiva.",
            acao_recomendada=acao,
            metadata={"fase": case.fase_atual, "status": case.status, "memorias_relacionadas": len(memorias)},
        )

    def _dias_ate(self, value: str) -> int | None:
        if not value:
            return None
        text = value.strip()
        try:
            return (datetime.fromisoformat(text.replace("Z", "+00:00")).date() - date.today()).days
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"):
            try:
                return (datetime.strptime(text[:10], fmt).date() - date.today()).days
            except ValueError:
                continue
        return None

    def _severity_rank(self, severity: str) -> int:
        return {"critica": 4, "alta": 3, "media": 2, "baixa": 1}.get(severity, 0)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
