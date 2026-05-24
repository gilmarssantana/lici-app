from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.schemas.alert import AlertRecord
from app.schemas.case import CaseRecord
from app.schemas.radar import RadarOpportunity
from app.schemas.triage import TriageItem
from app.services.alert_store import HybridAlertStore
from app.services.case_store import JsonCaseStore
from app.services.concorrente_store import HybridConcorrenteStore
from app.services.memory_store import JsonMemoryStore
from app.services.radar_store import HybridRadarStore
from app.services.triage_store import HybridTriageStore


class LiciDashboardService:
    """Camada somente-leitura para alimentar o futuro painel visual da LICI."""

    def __init__(
        self,
        radar_store: HybridRadarStore | None = None,
        triage_store: HybridTriageStore | None = None,
        alert_store: HybridAlertStore | None = None,
        case_store: JsonCaseStore | None = None,
        memory_store: JsonMemoryStore | None = None,
        concorrente_store: HybridConcorrenteStore | None = None,
    ):
        self.radar_store = radar_store or HybridRadarStore()
        self.triage_store = triage_store or HybridTriageStore()
        self.alert_store = alert_store or HybridAlertStore()
        self.case_store = case_store or JsonCaseStore()
        self.memory_store = memory_store or JsonMemoryStore(Path("/root/lici-app/memoria_viva"))
        self.concorrente_store = concorrente_store or HybridConcorrenteStore()

    def resumo(self, organization_id: str | None = None, user: dict[str, Any] | None = None) -> dict[str, Any]:
        oportunidades = self._oportunidades()
        if organization_id:
            oportunidades = [item for item in oportunidades if (getattr(item, "organization_id", None) or "default-org") == organization_id]
        triagem = self._triagem()
        alertas = self._alertas()
        casos = self._casos(organization_id=organization_id)
        memorias = self._memorias(organization_id=organization_id)
        risco_concorrencial = self._risco_concorrencial_dashboard(casos)
        return {
            "nome": "LICI Dashboard API",
            "organizacao": {
                "ativa": organization_id or "default-org",
                "role": (user or {}).get("organization_role"),
                "disponiveis": (user or {}).get("organizations", []),
                "usuarios_ativos": len((user or {}).get("organization_ids", [])),
            },
            "objetivo": "Central de comando visual da LICI para Radar, Triagem, Alertas, Casos e Memória.",
            "totais": {
                "oportunidades_radar": len(oportunidades),
                "triagem": len(triagem),
                "alertas": len(alertas),
                "alertas_nao_lidos": sum(1 for alerta in alertas if not alerta.lido),
                "casos_vivos": sum(1 for caso in casos if caso.status in {"ativo", "suspenso"}),
                "memorias": len(memorias),
                "casos_com_risco_concorrencial": len(risco_concorrencial),
            },
            "triagem_por_classificacao": self._counter_dict(item.classificacao for item in triagem),
            "alertas_por_severidade": self._counter_dict(alerta.severidade for alerta in alertas),
            "casos_por_fase": self._counter_dict(caso.fase_atual for caso in casos),
            "memorias_por_tipo": self._counter_dict(memoria.tipo for memoria in memorias),
            "score_medio_oportunidades": self._score_medio(oportunidades),
            "casos_com_acao_pendente": self._casos_com_acao_pendente(casos),
            "top_5_oportunidades": self._top_oportunidades(oportunidades, limit=5),
            "proximos_prazos": self._proximos_prazos(oportunidades, triagem, limit=10),
            "risco_concorrencial": risco_concorrencial,
        }

    def oportunidades(self, organization_id: str | None = None) -> dict[str, Any]:
        oportunidades = self._oportunidades()
        if organization_id:
            oportunidades = [item for item in oportunidades if (getattr(item, "organization_id", None) or "default-org") == organization_id]
        triagem = {item.oportunidade_id: item for item in self._triagem()}
        return {
            "total": len(oportunidades),
            "score_medio": self._score_medio(oportunidades),
            "top_5": self._top_oportunidades(oportunidades, limit=5),
            "por_uf": self._counter_dict(item.uf or "não informado" for item in oportunidades),
            "por_modalidade": self._counter_dict(item.modalidade or "não informado" for item in oportunidades),
            "itens": [self._oportunidade_dashboard(item, triagem.get(item.id)) for item in oportunidades],
        }

    def casos(self, organization_id: str | None = None) -> dict[str, Any]:
        casos = self._casos(organization_id=organization_id)
        pendentes = self._casos_com_acao_pendente(casos)
        return {
            "total": len(casos),
            "vivos": sum(1 for caso in casos if caso.status in {"ativo", "suspenso"}),
            "por_fase": self._counter_dict(caso.fase_atual for caso in casos),
            "por_status": self._counter_dict(caso.status for caso in casos),
            "com_acao_pendente": pendentes,
            "itens": [self._caso_dashboard(caso) for caso in casos],
        }

    def alertas(self) -> dict[str, Any]:
        alertas = sorted(self._alertas(), key=lambda a: (self._severity_rank(a.severidade), a.criado_em), reverse=True)
        return {
            "total": len(alertas),
            "nao_lidos": sum(1 for alerta in alertas if not alerta.lido),
            "por_severidade": self._counter_dict(alerta.severidade for alerta in alertas),
            "itens": [alerta.model_dump() for alerta in alertas],
        }

    def memorias(self, organization_id: str | None = None) -> dict[str, Any]:
        memorias = self._memorias(organization_id=organization_id)
        recentes = sorted(memorias, key=lambda m: m.data, reverse=True)[:10]
        return {
            "total": len(memorias),
            "por_tipo": self._counter_dict(memoria.tipo for memoria in memorias),
            "recentes": [memoria.model_dump() for memoria in recentes],
        }

    def kpis(self, organization_id: str | None = None) -> dict[str, Any]:
        oportunidades = self._oportunidades()
        if organization_id:
            oportunidades = [item for item in oportunidades if (getattr(item, "organization_id", None) or "default-org") == organization_id]
        triagem = self._triagem()
        alertas = self._alertas()
        casos = self._casos(organization_id=organization_id)
        return {
            "score_medio_oportunidades": self._score_medio(oportunidades),
            "taxa_prioridade_alta": self._percentual(
                sum(1 for item in triagem if item.classificacao == "prioridade_alta"), len(triagem)
            ),
            "alertas_criticos_abertos": sum(1 for a in alertas if a.severidade == "critica" and not a.lido),
            "alertas_nao_lidos": sum(1 for a in alertas if not a.lido),
            "casos_vivos": sum(1 for caso in casos if caso.status in {"ativo", "suspenso"}),
            "casos_com_acao_pendente_total": len(self._casos_com_acao_pendente(casos)),
            "casos_com_risco_concorrencial_total": len(self._risco_concorrencial_dashboard(casos)),
            "oportunidades_com_caso": sum(1 for o in oportunidades if o.caso_id),
            "oportunidades_sem_caso": sum(1 for o in oportunidades if not o.caso_id),
            "proximos_prazos_total": len(self._proximos_prazos(oportunidades, triagem, limit=1000)),
        }

    def _oportunidades(self) -> list[RadarOpportunity]:
        return self.radar_store.list()

    def _triagem(self) -> list[TriageItem]:
        return self.triage_store.list_queue()

    def _alertas(self) -> list[AlertRecord]:
        return self.alert_store.list_alerts()

    def _casos(self, organization_id: str | None = None) -> list[CaseRecord]:
        return self.case_store.list(organization_id=organization_id)

    def _memorias(self, organization_id: str | None = None):
        return self.memory_store.list(organization_id=organization_id)

    def _concorrentes(self):
        try:
            return self.concorrente_store.list()
        except Exception:
            return []

    def _counter_dict(self, values) -> dict[str, int]:
        return dict(Counter(str(value or "não informado") for value in values))

    def _score_medio(self, oportunidades: list[RadarOpportunity]) -> float:
        if not oportunidades:
            return 0.0
        return round(sum(item.score_preliminar for item in oportunidades) / len(oportunidades), 2)

    def _top_oportunidades(self, oportunidades: list[RadarOpportunity], limit: int) -> list[dict[str, Any]]:
        top = sorted(oportunidades, key=lambda o: (o.score_preliminar, o.valor_estimado or 0), reverse=True)[:limit]
        return [self._oportunidade_dashboard(item) for item in top]

    def _proximos_prazos(
        self, oportunidades: list[RadarOpportunity], triagem: list[TriageItem], limit: int
    ) -> list[dict[str, Any]]:
        triagem_por_id = {item.oportunidade_id: item for item in triagem}
        prazos = []
        for item in oportunidades:
            dias = self._dias_ate(item.data_encerramento)
            if dias is None:
                continue
            if dias <= 15:
                triage = triagem_por_id.get(item.id)
                prazos.append(
                    {
                        "oportunidade_id": item.id,
                        "pncp_id": item.pncp_id,
                        "orgao": item.orgao,
                        "objeto": item.objeto,
                        "data_encerramento": item.data_encerramento,
                        "dias_ate_encerramento": dias,
                        "score_preliminar": item.score_preliminar,
                        "classificacao_triagem": triage.classificacao if triage else None,
                        "severidade_sugerida": self._severidade_prazo(dias),
                    }
                )
        return sorted(prazos, key=lambda p: (p["dias_ate_encerramento"], -p["score_preliminar"]))[:limit]

    def _risco_concorrencial_dashboard(self, casos: list[CaseRecord]) -> list[dict[str, Any]]:
        concorrentes = self._concorrentes()
        riscos = []
        for caso in casos:
            relacionados = []
            orgao = (caso.orgao or "").casefold()
            objeto = (caso.objeto or "").casefold()
            for concorrente in concorrentes:
                orgao_match = any((o or "").casefold() and ((o or "").casefold() in orgao or orgao in (o or "").casefold()) for o in concorrente.orgaos_relacionados)
                segmento_match = bool(concorrente.segmento and concorrente.segmento.casefold() in objeto)
                if orgao_match or segmento_match:
                    relacionados.append(concorrente)
            if not relacionados:
                continue
            score = min(100, round(sum(c.score_risco for c in relacionados[:5]) / min(len(relacionados), 5)))
            riscos.append({
                "id": caso.id,
                "cliente": caso.cliente,
                "orgao": caso.orgao,
                "objeto": caso.objeto,
                "fase_atual": caso.fase_atual,
                "score_estrategico": caso.score_estrategico,
                "risco_concorrencial_score": score,
                "concorrentes_relevantes": [{"id": c.id, "nome": c.nome, "risco": c.risco_operacional, "score_risco": c.score_risco, "frequencia": c.frequencia} for c in relacionados[:5]],
                "acao_recomendada": "Blindar habilitação/proposta e monitorar falhas documentais, preço baixo e recursos dos concorrentes relacionados.",
            })
        return sorted(riscos, key=lambda item: item["risco_concorrencial_score"], reverse=True)

    def _casos_com_acao_pendente(self, casos: list[CaseRecord]) -> list[dict[str, Any]]:
        pendentes = []
        fases_acao = {"prospecção", "análise", "impugnação", "habilitação", "disputa", "recurso", "pagamento"}
        for caso in casos:
            riscos = " ".join(caso.riscos).casefold()
            if caso.status in {"ativo", "suspenso"} and (
                caso.fase_atual in fases_acao or any(t in riscos for t in ["prazo", "inabilitação", "pagamento", "recurso"])
            ):
                pendentes.append(
                    {
                        "id": caso.id,
                        "cliente": caso.cliente,
                        "orgao": caso.orgao,
                        "objeto": caso.objeto,
                        "fase_atual": caso.fase_atual,
                        "status": caso.status,
                        "score_estrategico": caso.score_estrategico,
                        "acao_recomendada": self._acao_caso(caso),
                    }
                )
        return sorted(pendentes, key=lambda c: c["score_estrategico"], reverse=True)

    def _oportunidade_dashboard(self, item: RadarOpportunity, triage: TriageItem | None = None) -> dict[str, Any]:
        return {
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
            "caso_id": item.caso_id,
            "classificacao_triagem": triage.classificacao if triage else None,
            "alerta_triagem": triage.sugerir_criacao_caso if triage else False,
            "link": item.link,
        }

    def _caso_dashboard(self, caso: CaseRecord) -> dict[str, Any]:
        risco = next((item for item in self._risco_concorrencial_dashboard([caso]) if item["id"] == caso.id), None)
        return {
            "id": caso.id,
            "cliente": caso.cliente,
            "orgao": caso.orgao,
            "objeto": caso.objeto,
            "modalidade": caso.modalidade,
            "fase_atual": caso.fase_atual,
            "status": caso.status,
            "score_estrategico": caso.score_estrategico,
            "riscos": caso.riscos,
            "oportunidades": caso.oportunidades,
            "atualizado_em": caso.atualizado_em,
            "risco_concorrencial": risco,
        }

    def _acao_caso(self, caso: CaseRecord) -> str:
        if caso.fase_atual in {"prospecção", "análise"}:
            return "Definir decisão operacional e checklist de habilitação/proposta."
        if caso.fase_atual == "impugnação":
            return "Protocolar/acompanhar impugnação e controlar prazo."
        if caso.fase_atual in {"habilitação", "disputa", "recurso"}:
            return "Verificar documentos, sessão, falhas de concorrentes e estratégia recursal."
        if caso.fase_atual == "pagamento":
            return "Acompanhar medição, nota, liquidação e eventual cobrança/reequilíbrio."
        return "Revisar próximo movimento operacional."

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

    def _severidade_prazo(self, dias: int) -> str:
        if dias <= 1:
            return "critica"
        if dias <= 3:
            return "alta"
        if dias <= 7:
            return "media"
        return "baixa"

    def _severity_rank(self, severity: str) -> int:
        return {"critica": 4, "alta": 3, "media": 2, "baixa": 1}.get(severity, 0)

    def _percentual(self, parte: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return round((parte / total) * 100, 2)
