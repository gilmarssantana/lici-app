from __future__ import annotations

import json
from pathlib import Path

from app.schemas.case import CaseRecord
from app.services.audit_log import audit_event
from app.services.case_pg_store import PostgresCaseStore

CASES_ROOT = Path("/root/lici-app/casos_vivos")


def migrate_cases_json_to_postgres(root: Path | str = CASES_ROOT) -> dict[str, int | str]:
    root = Path(root)
    pg_store = PostgresCaseStore()
    if not pg_store.available():
        audit_event("postgres_migration", "cases_json_to_postgres", "erro", {"motivo": "postgres_indisponivel"}, "fase2-cases")
        return {"status": "erro", "migrados": 0}

    migrated = 0
    seen: set[str] = set()
    for case_path in sorted(root.glob("*/case.json")):
        raw = json.loads(case_path.read_text(encoding="utf-8"))
        timeline_path = case_path.parent / "timeline.json"
        if timeline_path.exists():
            raw["historico_operacional"] = json.loads(timeline_path.read_text(encoding="utf-8"))
        case = CaseRecord(**raw)
        pg_store.upsert(case)
        migrated += 1
        seen.add(case.id)

    index_path = root / "casos.json"
    if index_path.exists():
        for item in json.loads(index_path.read_text(encoding="utf-8")):
            case = CaseRecord(**item)
            if case.id in seen:
                continue
            pg_store.upsert(case)
            migrated += 1
            seen.add(case.id)

    audit_event("postgres_migration", "cases_json_to_postgres", "ok", {"migrados": migrated}, "fase2-cases")
    return {"status": "ok", "migrados": migrated}


if __name__ == "__main__":
    print(migrate_cases_json_to_postgres())
