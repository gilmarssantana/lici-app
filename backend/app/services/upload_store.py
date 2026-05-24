from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.upload import UploadDocumentRecord
from app.services.audit_log import audit_event
from app.services.document_pg_store import PostgresUploadDocumentStore

STORAGE_ROOT = Path("/root/lici-app/storage")
EDITAIS_DIR = STORAGE_ROOT / "editais"
DOCUMENTOS_DB = STORAGE_ROOT / "documentos.json"


class JsonUploadStore:
    def __init__(self, db_path: Path | str = DOCUMENTOS_DB, editais_dir: Path | str = EDITAIS_DIR):
        self.db_path = Path(db_path)
        self.editais_dir = Path(editais_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.editais_dir.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            self._write_all([])

    def list(self) -> list[UploadDocumentRecord]:
        return [UploadDocumentRecord(**item) for item in self._read_all()]

    def get(self, document_id: str) -> UploadDocumentRecord | None:
        for item in self.list():
            if item.id == document_id:
                return item
        return None

    def create(self, record: UploadDocumentRecord) -> UploadDocumentRecord:
        items = self._read_all()
        items.append(record.model_dump(mode="json"))
        self._write_all(items)
        return record

    def update(self, record: UploadDocumentRecord) -> UploadDocumentRecord:
        items = self._read_all()
        out = []
        found = False
        for item in items:
            if item.get("id") == record.id:
                out.append(record.model_dump(mode="json"))
                found = True
            else:
                out.append(item)
        if not found:
            out.append(record.model_dump(mode="json"))
        self._write_all(out)
        return record

    def _read_all(self) -> list[dict]:
        if not self.db_path.exists():
            return []
        try:
            data = json.loads(self.db_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def _write_all(self, items: list[dict]) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.db_path.parent, delete=False) as tmp:
            json.dump(items, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.db_path)


class HybridUploadStore:
    """Upload dual-read/dual-write: PostgreSQL primeiro; JSON/arquivos físicos como fallback."""

    def __init__(self, json_store: JsonUploadStore | None = None, pg_store: PostgresUploadDocumentStore | None = None):
        self.json_store = json_store or JsonUploadStore()
        self.pg_store = pg_store or PostgresUploadDocumentStore()

    def list(self) -> list[UploadDocumentRecord]:
        try:
            if self.pg_store.available():
                return self.pg_store.list()
            audit_event("upload_engine", "postgres_fallback_json", "erro", {"operacao": "list", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("upload_engine", "postgres_fallback_json", "erro", {"operacao": "list", "erro": str(exc)})
        return self.json_store.list()

    def get(self, document_id: str) -> UploadDocumentRecord | None:
        try:
            if self.pg_store.available():
                return self.pg_store.get(document_id)
            audit_event("upload_engine", "postgres_fallback_json", "erro", {"operacao": "get", "motivo": "postgres_indisponivel", "document_id": document_id}, document_id)
        except Exception as exc:
            audit_event("upload_engine", "postgres_fallback_json", "erro", {"operacao": "get", "document_id": document_id, "erro": str(exc)}, document_id)
        return self.json_store.get(document_id)

    def create(self, record: UploadDocumentRecord) -> UploadDocumentRecord:
        saved = self.json_store.create(record)
        self._try_pg(saved, "create")
        return saved

    def update(self, record: UploadDocumentRecord) -> UploadDocumentRecord:
        saved = self.json_store.update(record)
        self._try_pg(saved, "update")
        return saved

    def _try_pg(self, record: UploadDocumentRecord, operation: str) -> None:
        try:
            if self.pg_store.available():
                self.pg_store.upsert(record)
                audit_event("upload_engine", "dual_write_postgres", "ok", {"operacao": operation}, record.id)
            else:
                audit_event("upload_engine", "dual_write_postgres", "erro", {"operacao": operation, "motivo": "postgres_indisponivel"}, record.id)
        except Exception as exc:
            audit_event("upload_engine", "dual_write_postgres", "erro", {"operacao": operation, "erro": str(exc)}, record.id)
