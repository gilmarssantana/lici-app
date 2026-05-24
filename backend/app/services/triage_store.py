from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from app.schemas.triage import TriageItem, TriageRunLog
from app.services.audit_log import audit_event
from app.services.radar_pg_store import PostgresTriageStore


class JsonTriageStore:
    def __init__(self, root: Path | str = "/root/lici-app/triagem"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.queue_path = self.root / "fila.json"
        self.logs_path = self.root / "logs.json"
        if not self.queue_path.exists():
            self._write_json(self.queue_path, [])
        if not self.logs_path.exists():
            self._write_json(self.logs_path, [])

    def list_queue(self) -> list[TriageItem]:
        raw = self._read_json(self.queue_path, [])
        return [TriageItem(**item) for item in raw]

    def write_queue(self, items: list[TriageItem]) -> list[TriageItem]:
        self._write_json(self.queue_path, [item.model_dump() for item in items])
        return items

    def get_item(self, opportunity_id: str) -> TriageItem | None:
        for item in self.list_queue():
            if item.oportunidade_id == opportunity_id or item.id == opportunity_id:
                return item
        return None

    def update_item(self, updated: TriageItem) -> TriageItem:
        items = self.list_queue()
        for idx, item in enumerate(items):
            if item.id == updated.id:
                items[idx] = updated
                self.write_queue(items)
                return updated
        items.append(updated)
        self.write_queue(items)
        return updated

    def list_logs(self) -> list[TriageRunLog]:
        raw = self._read_json(self.logs_path, [])
        return [TriageRunLog(**item) for item in raw]

    def append_log(self, log: TriageRunLog) -> TriageRunLog:
        logs = self.list_logs()
        logs.append(log)
        self._write_json(self.logs_path, [item.model_dump() for item in logs])
        return log

    def _read_json(self, path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)


class HybridTriageStore:
    """Triagem dual-read/dual-write: read PostgreSQL first with JSON fallback; write JSON mandatory + PostgreSQL best-effort."""

    def __init__(self, json_store: JsonTriageStore | None = None, pg_store: PostgresTriageStore | None = None):
        self.json_store = json_store or JsonTriageStore()
        self.pg_store = pg_store or PostgresTriageStore()

    def list_queue(self) -> list[TriageItem]:
        try:
            if self.pg_store.available():
                return self.pg_store.list_queue()
            audit_event("triage_engine", "postgres_fallback_json", "erro", {"operacao": "list_queue", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("triage_engine", "postgres_fallback_json", "erro", {"operacao": "list_queue", "erro": str(exc)})
        return self.json_store.list_queue()

    def write_queue(self, items: list[TriageItem]) -> list[TriageItem]:
        saved = self.json_store.write_queue(items)
        self._try_pg_queue(saved, "write_queue")
        return saved

    def get_item(self, opportunity_id: str) -> TriageItem | None:
        try:
            if self.pg_store.available():
                return self.pg_store.get_item(opportunity_id)
            audit_event("triage_engine", "postgres_fallback_json", "erro", {"operacao": "get_item", "motivo": "postgres_indisponivel", "opportunity_id": opportunity_id}, opportunity_id)
        except Exception as exc:
            audit_event("triage_engine", "postgres_fallback_json", "erro", {"operacao": "get_item", "opportunity_id": opportunity_id, "erro": str(exc)}, opportunity_id)
        return self.json_store.get_item(opportunity_id)

    def update_item(self, updated: TriageItem) -> TriageItem:
        saved = self.json_store.update_item(updated)
        self._try_pg_item(saved, "update_item")
        return saved

    def list_logs(self) -> list[TriageRunLog]:
        try:
            if self.pg_store.available():
                return self.pg_store.list_logs()
            audit_event("triage_engine", "postgres_fallback_json", "erro", {"operacao": "list_logs", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("triage_engine", "postgres_fallback_json", "erro", {"operacao": "list_logs", "erro": str(exc)})
        return self.json_store.list_logs()

    def append_log(self, log: TriageRunLog) -> TriageRunLog:
        saved = self.json_store.append_log(log)
        try:
            if self.pg_store.available():
                self.pg_store.append_log(saved)
                audit_event("triage_engine", "dual_write_postgres", "ok", {"operacao": "append_log"}, saved.id)
            else:
                audit_event("triage_engine", "dual_write_postgres", "erro", {"operacao": "append_log", "motivo": "postgres_indisponivel"}, saved.id)
        except Exception as exc:
            audit_event("triage_engine", "dual_write_postgres", "erro", {"operacao": "append_log", "erro": str(exc)}, saved.id)
        return saved

    def _try_pg_queue(self, items: list[TriageItem], operation: str) -> None:
        try:
            if self.pg_store.available():
                self.pg_store.write_queue(items)
                audit_event("triage_engine", "dual_write_postgres", "ok", {"operacao": operation, "total": len(items)})
            else:
                audit_event("triage_engine", "dual_write_postgres", "erro", {"operacao": operation, "motivo": "postgres_indisponivel", "total": len(items)})
        except Exception as exc:
            audit_event("triage_engine", "dual_write_postgres", "erro", {"operacao": operation, "erro": str(exc), "total": len(items)})

    def _try_pg_item(self, item: TriageItem, operation: str) -> None:
        try:
            if self.pg_store.available():
                self.pg_store.upsert_item(item)
                audit_event("triage_engine", "dual_write_postgres", "ok", {"operacao": operation}, item.id)
            else:
                audit_event("triage_engine", "dual_write_postgres", "erro", {"operacao": operation, "motivo": "postgres_indisponivel"}, item.id)
        except Exception as exc:
            audit_event("triage_engine", "dual_write_postgres", "erro", {"operacao": operation, "erro": str(exc)}, item.id)
