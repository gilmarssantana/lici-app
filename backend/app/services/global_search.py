from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.alert_store import HybridAlertStore
from app.services.case_store import HybridCaseStore
from app.services.consultor_store import HybridConsultorStore
from app.services.concorrente_store import HybridConcorrenteStore
from app.services.document_generator_store import HybridGeneratedDocumentStore
from app.services.memory_store import HybridMemoryStore
from app.services.orgao_store import HybridOrgaoStore
from app.services.radar_store import HybridRadarStore
from app.services.upload_store import HybridUploadStore


class LiciGlobalSearchService:
    """Busca operacional unificada, somente leitura, sobre domínios já existentes."""

    def __init__(self):
        self.case_store = HybridCaseStore()
        self.memory_store = HybridMemoryStore(Path("/root/lici-app/memoria_viva"))
        self.radar_store = HybridRadarStore()
        self.alert_store = HybridAlertStore()
        self.upload_store = HybridUploadStore()
        self.generated_store = HybridGeneratedDocumentStore()
        self.consultor_store = HybridConsultorStore()
        self.concorrente_store = HybridConcorrenteStore()
        self.orgao_store = HybridOrgaoStore()

    def search(self, q: str, limit: int = 12) -> dict[str, Any]:
        termo = (q or "").casefold().strip()
        limit = max(1, min(limit, 50))
        buckets: dict[str, list[dict[str, Any]]] = {
            "casos": [],
            "memorias": [],
            "oportunidades": [],
            "alertas": [],
            "documentos": [],
            "clientes_consultor": [],
            "concorrentes": [],
            "orgaos": [],
        }
        if not termo:
            return {"q": q, "total": 0, "resultados": buckets, "flat": []}

        self._fill(buckets["casos"], "caso", self.case_store.list(), termo, ["id", "cliente", "orgao", "objeto", "modalidade", "fase_atual", "status", "riscos", "oportunidades"], limit)
        self._fill(buckets["memorias"], "memoria", self.memory_store.list(), termo, ["id", "tipo", "titulo", "descricao", "contexto", "estrategia", "aprendizado", "uso_futuro", "tags"], limit)
        self._fill(buckets["oportunidades"], "oportunidade", self.radar_store.list(), termo, ["id", "pncp_id", "orgao", "uf", "objeto", "modalidade", "score_preliminar"], limit)
        self._fill(buckets["alertas"], "alerta", self.alert_store.list_alerts(), termo, ["id", "titulo", "mensagem", "severidade", "orgao", "objeto", "risco", "acao_recomendada"], limit)
        uploaded = [("documento_upload", item) for item in self.upload_store.list()]
        generated = [("documento_gerado", item) for item in self.generated_store.list()]
        self._fill_documents(buckets["documentos"], uploaded + generated, termo, limit)
        self._fill(buckets["clientes_consultor"], "cliente_consultor", self.consultor_store.list_clientes(), termo, ["id", "nome", "documento", "segmento", "uf", "status", "observacoes", "contatos"], limit)
        self._fill(buckets["concorrentes"], "concorrente", self.concorrente_store.list(), termo, ["id", "nome", "cnpj", "segmento", "uf", "observacoes_estrategicas", "risco_operacional", "padroes_documentais", "padroes_preco", "orgaos_relacionados", "casos_relacionados"], limit)
        self._fill(buckets["orgaos"], "orgao", self.orgao_store.list(), termo, ["id", "nome", "cnpj", "uf", "esfera", "poder", "perfil", "observacoes"], limit)

        flat = []
        for group, items in buckets.items():
            for item in items:
                flat.append({**item, "grupo": group})
        flat.sort(key=lambda item: item.get("score", 0), reverse=True)
        total = sum(len(items) for items in buckets.values())
        return {"q": q, "total": total, "resultados": buckets, "flat": flat[: limit * 7]}

    def _fill(self, out: list[dict[str, Any]], tipo: str, items: list[Any], termo: str, fields: list[str], limit: int) -> None:
        for item in items:
            data = self._dump(item)
            haystack = self._haystack(data, fields)
            if termo not in haystack:
                continue
            out.append(self._result(tipo, data, termo, fields))
            if len(out) >= limit:
                return

    def _fill_documents(self, out: list[dict[str, Any]], items: list[tuple[str, Any]], termo: str, limit: int) -> None:
        fields = ["id", "nome_original", "titulo", "tipo", "status", "extensao", "arquivo", "texto", "erro"]
        for tipo, item in items:
            data = self._dump(item)
            if termo not in self._haystack(data, fields):
                continue
            out.append(self._result(tipo, data, termo, fields))
            if len(out) >= limit:
                return

    def _result(self, tipo: str, data: dict[str, Any], termo: str, fields: list[str]) -> dict[str, Any]:
        title = data.get("titulo") or data.get("nome") or data.get("nome_original") or data.get("orgao") or data.get("cliente") or data.get("id")
        subtitle = data.get("objeto") or data.get("descricao") or data.get("mensagem") or data.get("segmento") or data.get("status") or ""
        score = 100 if termo in str(title or "").casefold() else 70
        return {
            "tipo": tipo,
            "id": data.get("id"),
            "titulo": title,
            "subtitulo": subtitle,
            "score": score,
            "metadados": self._metadata(data),
            "payload": data,
        }

    def _dump(self, item: Any) -> dict[str, Any]:
        if hasattr(item, "model_dump"):
            return item.model_dump(mode="json")
        if isinstance(item, dict):
            return item
        return dict(item)

    def _haystack(self, data: dict[str, Any], fields: list[str]) -> str:
        values = []
        for field in fields:
            value = data.get(field)
            if isinstance(value, list):
                values.extend(str(v) for v in value)
            elif isinstance(value, dict):
                values.append(" ".join(str(v) for v in value.values()))
            elif value is not None:
                values.append(str(value))
        return "\n".join(values).casefold()

    def _metadata(self, data: dict[str, Any]) -> dict[str, Any]:
        keys = ["orgao", "uf", "status", "fase_atual", "score_estrategico", "score_preliminar", "tipo", "severidade", "criado_em", "atualizado_em"]
        return {key: data.get(key) for key in keys if data.get(key) not in (None, "")}
