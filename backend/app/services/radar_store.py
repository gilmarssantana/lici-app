from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.radar import RadarOpportunity
from app.services.audit_log import audit_event
from app.services.radar_pg_store import PostgresRadarStore


class JsonRadarStore:
    def __init__(self, path: Path | str = "/root/lici-app/radar/oportunidades.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_all([])

    def list(self) -> list[RadarOpportunity]:
        return sorted(self._read_all(), key=lambda o: o.atualizado_em, reverse=True)

    def get(self, opportunity_id: str) -> RadarOpportunity | None:
        for item in self._read_all():
            if item.id == opportunity_id:
                return item
        return None

    def upsert_many(self, opportunities: list[RadarOpportunity]) -> list[RadarOpportunity]:
        existing = self._read_all()
        by_key: dict[str, RadarOpportunity] = {}
        for item in existing:
            by_key[self._key(item)] = item
        saved: list[RadarOpportunity] = []
        for item in opportunities:
            key = self._key(item)
            current = by_key.get(key)
            if current:
                item.id = current.id
                item.criado_em = current.criado_em
                if current.caso_id and not item.caso_id:
                    item.caso_id = current.caso_id
            by_key[key] = item
            saved.append(item)
        self._write_all(list(by_key.values()))
        return saved

    def update(self, opportunity: RadarOpportunity) -> RadarOpportunity:
        items = self._read_all()
        for idx, item in enumerate(items):
            if item.id == opportunity.id:
                items[idx] = opportunity
                self._write_all(items)
                return opportunity
        items.append(opportunity)
        self._write_all(items)
        return opportunity

    def _key(self, opportunity: RadarOpportunity) -> str:
        return opportunity.pncp_id or f"{opportunity.orgao}|{opportunity.objeto}|{opportunity.data_publicacao}|{opportunity.valor_estimado}"

    def _read_all(self) -> list[RadarOpportunity]:
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [RadarOpportunity(**item) for item in raw]

    def _write_all(self, items: list[RadarOpportunity]) -> None:
        data = [item.model_dump() for item in items]
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.path.parent, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.path)


class HybridRadarStore:
    """Radar dual-read/dual-write store: read PostgreSQL first with JSON fallback; write JSON mandatory + PostgreSQL best-effort."""

    def __init__(self, json_store: JsonRadarStore | None = None, pg_store: PostgresRadarStore | None = None):
        self.json_store = json_store or JsonRadarStore()
        self.pg_store = pg_store or PostgresRadarStore()

    def list(self) -> list[RadarOpportunity]:
        try:
            if self.pg_store.available():
                return self.pg_store.list()
            audit_event("radar_engine", "postgres_fallback_json", "erro", {"operacao": "list", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("radar_engine", "postgres_fallback_json", "erro", {"operacao": "list", "erro": str(exc)})
        return self.json_store.list()

    def get(self, opportunity_id: str) -> RadarOpportunity | None:
        try:
            if self.pg_store.available():
                return self.pg_store.get(opportunity_id)
            audit_event("radar_engine", "postgres_fallback_json", "erro", {"operacao": "get", "motivo": "postgres_indisponivel", "opportunity_id": opportunity_id}, opportunity_id)
        except Exception as exc:
            audit_event("radar_engine", "postgres_fallback_json", "erro", {"operacao": "get", "opportunity_id": opportunity_id, "erro": str(exc)}, opportunity_id)
        return self.json_store.get(opportunity_id)

    def upsert_many(self, opportunities: list[RadarOpportunity]) -> list[RadarOpportunity]:
        saved = self.json_store.upsert_many(opportunities)
        self._try_pg_many(saved, "upsert_many")
        return saved

    def update(self, opportunity: RadarOpportunity) -> RadarOpportunity:
        saved = self.json_store.update(opportunity)
        self._try_pg(saved, "update")
        return saved

    def _try_pg_many(self, opportunities: list[RadarOpportunity], operation: str) -> None:
        try:
            if self.pg_store.available():
                self.pg_store.upsert_many(opportunities)
                audit_event("radar_engine", "dual_write_postgres", "ok", {"operacao": operation, "total": len(opportunities)})
            else:
                audit_event("radar_engine", "dual_write_postgres", "erro", {"operacao": operation, "motivo": "postgres_indisponivel", "total": len(opportunities)})
        except Exception as exc:
            audit_event("radar_engine", "dual_write_postgres", "erro", {"operacao": operation, "erro": str(exc), "total": len(opportunities)})

    def _try_pg(self, opportunity: RadarOpportunity, operation: str) -> None:
        try:
            if self.pg_store.available():
                self.pg_store.upsert(opportunity)
                audit_event("radar_engine", "dual_write_postgres", "ok", {"operacao": operation}, opportunity.id)
            else:
                audit_event("radar_engine", "dual_write_postgres", "erro", {"operacao": operation, "motivo": "postgres_indisponivel"}, opportunity.id)
        except Exception as exc:
            audit_event("radar_engine", "dual_write_postgres", "erro", {"operacao": operation, "erro": str(exc)}, opportunity.id)
