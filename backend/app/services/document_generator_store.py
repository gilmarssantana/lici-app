from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.document_generator import GeneratedDocumentRecord
from app.services.audit_log import audit_event
from app.services.document_pg_store import PostgresGeneratedDocumentStore

GENERATED_DIR = Path("/root/lici-app/storage/documentos_gerados")
GENERATED_INDEX = GENERATED_DIR / "index.json"


class JsonGeneratedDocumentStore:
    def __init__(self, root: Path | str = GENERATED_DIR):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        if not self.index_path.exists():
            self._write_all([])

    def list(self, organization_id: str | None = None) -> list[GeneratedDocumentRecord]:
        items = [GeneratedDocumentRecord(**item) for item in self._read_all()]
        if organization_id:
            items = [item for item in items if (item.organization_id or "default-org") == organization_id]
        return sorted(items, key=lambda d: d.criado_em, reverse=True)

    def get(self, document_id: str, organization_id: str | None = None) -> GeneratedDocumentRecord | None:
        for item in self.list(organization_id=organization_id):
            if item.id == document_id:
                return item
        return None

    def create(self, record: GeneratedDocumentRecord) -> GeneratedDocumentRecord:
        Path(record.caminho).write_text(record.texto, encoding="utf-8")
        items = self._read_all()
        items.append(record.model_dump(mode="json"))
        self._write_all(items)
        return record

    def update(self, record: GeneratedDocumentRecord) -> GeneratedDocumentRecord:
        Path(record.caminho).write_text(record.texto, encoding="utf-8")
        items = self._read_all(); found = False; out = []
        for item in items:
            if item.get('id') == record.id:
                out.append(record.model_dump(mode='json')); found = True
            else:
                out.append(item)
        if not found: out.append(record.model_dump(mode='json'))
        self._write_all(out)
        return record

    def _read_all(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def _write_all(self, items: list[dict]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.root, delete=False) as tmp:
            json.dump(items, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.index_path)


class HybridGeneratedDocumentStore:
    """Documentos gerados dual-read/dual-write: PostgreSQL primeiro; JSON/arquivo físico como fallback."""

    def __init__(self, json_store: JsonGeneratedDocumentStore | None = None, pg_store: PostgresGeneratedDocumentStore | None = None):
        self.json_store = json_store or JsonGeneratedDocumentStore()
        self.pg_store = pg_store or PostgresGeneratedDocumentStore()

    def list(self, organization_id: str | None = None) -> list[GeneratedDocumentRecord]:
        try:
            if self.pg_store.available():
                items = self.pg_store.list()
                if organization_id:
                    items = [item for item in items if (item.organization_id or "default-org") == organization_id]
                return items
            audit_event("document_generator", "postgres_fallback_json", "erro", {"operacao": "list", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("document_generator", "postgres_fallback_json", "erro", {"operacao": "list", "erro": str(exc)})
        return self.json_store.list(organization_id=organization_id)

    def get(self, document_id: str, organization_id: str | None = None) -> GeneratedDocumentRecord | None:
        try:
            if self.pg_store.available():
                for item in self.pg_store.list():
                    if item.id == document_id and (organization_id is None or (item.organization_id or 'default-org') == organization_id):
                        return item
        except Exception as exc:
            audit_event('document_generator', 'postgres_fallback_json', 'erro', {'operacao': 'get', 'document_id': document_id, 'erro': str(exc)}, document_id)
        return self.json_store.get(document_id, organization_id=organization_id)

    def exists(self, document_id: str) -> bool:
        return self.get(document_id) is not None

    def update(self, record: GeneratedDocumentRecord) -> GeneratedDocumentRecord:
        saved = self.json_store.update(record)
        try:
            if self.pg_store.available():
                self.pg_store.upsert(saved)
                audit_event('document_generator', 'dual_write_postgres', 'ok', {'operacao': 'update'}, saved.id)
        except Exception as exc:
            audit_event('document_generator', 'dual_write_postgres', 'erro', {'operacao': 'update', 'erro': str(exc)}, saved.id)
        return saved

    def create(self, record: GeneratedDocumentRecord) -> GeneratedDocumentRecord:
        saved = self.json_store.create(record)
        try:
            if self.pg_store.available():
                self.pg_store.upsert(saved)
                audit_event("document_generator", "dual_write_postgres", "ok", {"operacao": "create"}, saved.id)
            else:
                audit_event("document_generator", "dual_write_postgres", "erro", {"operacao": "create", "motivo": "postgres_indisponivel"}, saved.id)
        except Exception as exc:
            audit_event("document_generator", "dual_write_postgres", "erro", {"operacao": "create", "erro": str(exc)}, saved.id)
        return saved
