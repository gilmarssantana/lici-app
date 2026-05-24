from __future__ import annotations

import json
from pathlib import Path

from app.schemas.memory import MemoryRecord
from app.services.audit_log import audit_event
from app.services.memory_pg_store import PostgresMemoryStore

MEMORY_ROOT = Path("/root/lici-app/memoria_viva")


def migrate_memory_json_to_postgres(root: Path | str = MEMORY_ROOT) -> dict[str, int | str]:
    root = Path(root)
    pg_store = PostgresMemoryStore()
    if not pg_store.available():
        audit_event("postgres_migration", "memory_json_to_postgres", "erro", {"motivo": "postgres_indisponivel"}, "fase3-memory")
        return {"status": "erro", "migrados": 0}

    migrated = 0
    seen: set[str] = set()
    main = root / "memorias.json"
    if main.exists():
        for item in json.loads(main.read_text(encoding="utf-8")):
            record = MemoryRecord(**item)
            pg_store.upsert(record)
            migrated += 1
            seen.add(record.id)

    # Some historical mirrors are JSON files by type; migrate any valid records not in memorias.json.
    for path in sorted(root.glob("**/*.json")):
        if path.name == "memorias.json":
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                candidates = raw
            elif isinstance(raw, dict):
                candidates = [raw]
            else:
                continue
            for item in candidates:
                if not isinstance(item, dict) or "id" not in item or "tipo" not in item:
                    continue
                record = MemoryRecord(**item)
                if record.id in seen:
                    continue
                pg_store.upsert(record)
                migrated += 1
                seen.add(record.id)
        except Exception as exc:
            audit_event("postgres_migration", "memory_json_item_skip", "erro", {"arquivo": str(path), "erro": str(exc)}, "fase3-memory")

    audit_event("postgres_migration", "memory_json_to_postgres", "ok", {"migrados": migrated}, "fase3-memory")
    return {"status": "ok", "migrados": migrated}


if __name__ == "__main__":
    print(migrate_memory_json_to_postgres())
