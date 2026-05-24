from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.memory import MemoryCreate, MemoryRecord
from app.services.audit_log import audit_event
from app.services.memory_pg_store import PostgresMemoryStore


class JsonMemoryStore:
    """JSON-backed memory store."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "memorias.json"
        if not self.db_path.exists():
            self._write_all([])

    def create(self, payload: MemoryCreate, organization_id: str | None = None) -> MemoryRecord:
        if organization_id and not payload.organization_id:
            payload = payload.model_copy(update={"organization_id": organization_id})
        record = MemoryRecord(**payload.model_dump())
        return self.create_record(record)

    def create_record(self, record: MemoryRecord) -> MemoryRecord:
        items = self._read_all()
        # idempotent append/update for migration and dual-write safety
        replaced = False
        for idx, item in enumerate(items):
            if item.id == record.id:
                items[idx] = record
                replaced = True
                break
        if not replaced:
            items.append(record)
        self._write_all(items)
        self._append_type_file(record)
        return record

    def list(self, tipo: str | None = None, organization_id: str | None = None) -> list[MemoryRecord]:
        items = self._read_all()
        if tipo:
            items = [item for item in items if item.tipo == tipo]
        if organization_id:
            items = [item for item in items if (item.organization_id or "default-org") == organization_id]
        return sorted(items, key=lambda item: item.data, reverse=True)

    def get(self, memory_id: str, organization_id: str | None = None) -> MemoryRecord | None:
        for item in self._read_all():
            if item.id == memory_id and (organization_id is None or (item.organization_id or 'default-org') == organization_id):
                return item
        return None

    def search(self, termo: str, tipo: str | None = None, organization_id: str | None = None) -> list[MemoryRecord]:
        termo_norm = termo.casefold().strip()
        items = self.list(tipo=tipo, organization_id=organization_id)
        if not termo_norm:
            return items
        return [item for item in items if termo_norm in self._haystack(item)]

    def _haystack(self, item: MemoryRecord) -> str:
        values = [
            item.tipo,
            item.titulo,
            item.descricao,
            item.contexto,
            item.estrategia,
            item.resultado,
            item.aprendizado,
            item.uso_futuro,
            item.fonte,
            " ".join(item.tags),
        ]
        return "\n".join(values).casefold()

    def _read_all(self) -> list[MemoryRecord]:
        raw = json.loads(self.db_path.read_text(encoding="utf-8"))
        return [MemoryRecord(**item) for item in raw]

    def _write_all(self, items: list[MemoryRecord]) -> None:
        data = [item.model_dump() for item in items]
        self.root.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.root, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.db_path)

    def _append_type_file(self, item: MemoryRecord) -> None:
        type_dir = self.root / self._type_dir(item.tipo)
        type_dir.mkdir(parents=True, exist_ok=True)
        md_path = type_dir / f"{item.id}.md"
        md_path.write_text(
            f"# {item.titulo}\n\n"
            f"- id: {item.id}\n"
            f"- data: {item.data}\n"
            f"- tipo: {item.tipo}\n"
            f"- confiança: {item.confianca}\n"
            f"- tags: {', '.join(item.tags)}\n"
            f"- fonte: {item.fonte}\n\n"
            f"## Descrição\n\n{item.descricao}\n\n"
            f"## Contexto\n\n{item.contexto}\n\n"
            f"## Estratégia\n\n{item.estrategia}\n\n"
            f"## Resultado\n\n{item.resultado}\n\n"
            f"## Aprendizado\n\n{item.aprendizado}\n\n"
            f"## Uso futuro\n\n{item.uso_futuro}\n",
            encoding="utf-8",
        )

    def _type_dir(self, tipo: str) -> str:
        mapping = {
            "orgao": "orgaos",
            "concorrente": "concorrentes",
            "tese": "teses",
            "vitoria": "vitorias",
            "perda": "perdas",
            "risco": "riscos",
            "padrao": "padroes",
            "contrato": "contratos",
            "impugnacao": "impugnacoes",
            "recurso": "recursos",
        }
        return mapping.get(tipo, tipo)


class HybridMemoryStore:
    """Dual-read/dual-write memory store for PostgreSQL Fase 3."""

    def __init__(self, root: Path, json_store: JsonMemoryStore | None = None, pg_store: PostgresMemoryStore | None = None):
        self.json_store = json_store or JsonMemoryStore(root)
        self.pg_store = pg_store or PostgresMemoryStore()

    def create(self, payload: MemoryCreate, organization_id: str | None = None) -> MemoryRecord:
        record = self.json_store.create(payload, organization_id=organization_id)
        self._write_pg(record, "create")
        return record

    def create_record(self, record: MemoryRecord) -> MemoryRecord:
        saved = self.json_store.create_record(record)
        self._write_pg(saved, "create_record")
        return saved

    def get(self, memory_id: str, organization_id: str | None = None) -> MemoryRecord | None:
        try:
            if self.pg_store.available():
                for item in self.pg_store.list(tipo=None):
                    if item.id == memory_id and (organization_id is None or (item.organization_id or 'default-org') == organization_id):
                        return item
        except Exception as exc:
            audit_event('memory', 'postgres_fallback_json', 'erro', {'operacao': 'get', 'memory_id': memory_id, 'erro': str(exc)}, memory_id)
        return self.json_store.get(memory_id, organization_id=organization_id)

    def exists(self, memory_id: str) -> bool:
        return self.get(memory_id) is not None

    def upsert(self, record: MemoryRecord) -> MemoryRecord:
        saved = self.json_store.create_record(record)
        self._write_pg(saved, 'upsert')
        return saved

    def list(self, tipo: str | None = None, organization_id: str | None = None) -> list[MemoryRecord]:
        try:
            if self.pg_store.available():
                items = self.pg_store.list(tipo=tipo)
                if organization_id:
                    items = [item for item in items if (item.organization_id or "default-org") == organization_id]
                return items
        except Exception as exc:
            audit_event("memory", "postgres_fallback_json", "erro", {"operacao": "list", "tipo": tipo, "erro": str(exc)})
        return self.json_store.list(tipo=tipo, organization_id=organization_id)

    def search(self, termo: str, tipo: str | None = None, organization_id: str | None = None) -> list[MemoryRecord]:
        try:
            if self.pg_store.available():
                items = self.pg_store.search(termo=termo, tipo=tipo)
                if organization_id:
                    items = [item for item in items if (item.organization_id or "default-org") == organization_id]
                return items
        except Exception as exc:
            audit_event("memory", "postgres_fallback_json", "erro", {"operacao": "search", "termo": termo, "tipo": tipo, "erro": str(exc)})
        return self.json_store.search(termo=termo, tipo=tipo, organization_id=organization_id)

    def _write_pg(self, record: MemoryRecord, operation: str) -> None:
        try:
            if self.pg_store.available():
                self.pg_store.upsert(record)
                audit_event("memory", "dual_write_postgres", "ok", {"operacao": operation, "tipo": record.tipo, "titulo": record.titulo}, record.id)
            else:
                audit_event("memory", "dual_write_postgres", "erro", {"operacao": operation, "motivo": "postgres_indisponivel", "tipo": record.tipo}, record.id)
        except Exception as exc:
            audit_event("memory", "dual_write_postgres", "erro", {"operacao": operation, "erro": str(exc), "tipo": record.tipo}, record.id)
