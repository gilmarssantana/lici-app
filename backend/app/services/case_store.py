from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.case import CaseRecord
from app.services.audit_log import audit_event
from app.services.case_pg_store import PostgresCaseStore


class JsonCaseStore:
    def __init__(self, root: Path | str = "/root/lici-app/casos_vivos"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "casos.json"
        if not self.db_path.exists():
            self._write_all([])

    def create(self, case: CaseRecord) -> CaseRecord:
        items = self._read_all()
        items.append(case)
        self._write_all(items)
        self._write_case_file(case)
        return case

    def list(self, organization_id: str | None = None) -> list[CaseRecord]:
        items = self._read_all()
        if organization_id:
            items = [case for case in items if (case.organization_id or "default-org") == organization_id]
        return sorted(items, key=lambda c: c.atualizado_em, reverse=True)

    def get(self, case_id: str, organization_id: str | None = None) -> CaseRecord | None:
        for case in self._read_all():
            if case.id == case_id and (organization_id is None or (case.organization_id or "default-org") == organization_id):
                return case
        return None

    def update(self, case: CaseRecord) -> CaseRecord:
        items = self._read_all()
        for idx, item in enumerate(items):
            if item.id == case.id:
                items[idx] = case
                self._write_all(items)
                self._write_case_file(case)
                return case
        items.append(case)
        self._write_all(items)
        self._write_case_file(case)
        return case

    def _read_all(self) -> list[CaseRecord]:
        raw = json.loads(self.db_path.read_text(encoding="utf-8"))
        return [CaseRecord(**item) for item in raw]

    def _write_all(self, items: list[CaseRecord]) -> None:
        data = [item.model_dump() for item in items]
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.root, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.db_path)

    def _write_case_file(self, case: CaseRecord) -> None:
        case_dir = self.root / case.id
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "case.json").write_text(
            json.dumps(case.model_dump(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        timeline = [event.model_dump() for event in case.historico_operacional]
        (case_dir / "timeline.json").write_text(
            json.dumps(timeline, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


class HybridCaseStore:
    """Dual-read/dual-write store for PostgreSQL Fase 2.

    - Reads PostgreSQL first, falls back to JSON.
    - Writes JSON first and then PostgreSQL.
    - PostgreSQL failures are audited and never break case operations.
    """

    def __init__(self, json_store: JsonCaseStore | None = None, pg_store: PostgresCaseStore | None = None):
        self.json_store = json_store or JsonCaseStore()
        self.pg_store = pg_store or PostgresCaseStore()

    def create(self, case: CaseRecord) -> CaseRecord:
        created = self.json_store.create(case)
        self._write_pg(created, "create")
        return created

    def list(self, organization_id: str | None = None) -> list[CaseRecord]:
        try:
            if self.pg_store.available():
                items = self.pg_store.list()
                if organization_id:
                    items = [case for case in items if (case.organization_id or "default-org") == organization_id]
                return items
        except Exception as exc:
            audit_event("case_engine", "postgres_fallback_json", "erro", {"operacao": "list", "erro": str(exc)})
        return self.json_store.list(organization_id=organization_id)

    def get(self, case_id: str, organization_id: str | None = None) -> CaseRecord | None:
        try:
            if self.pg_store.available():
                case = self.pg_store.get(case_id)
                if case and (organization_id is None or (case.organization_id or "default-org") == organization_id):
                    return case
        except Exception as exc:
            audit_event("case_engine", "postgres_fallback_json", "erro", {"operacao": "get", "case_id": case_id, "erro": str(exc)}, case_id)
        return self.json_store.get(case_id, organization_id=organization_id)

    def update(self, case: CaseRecord) -> CaseRecord:
        updated = self.json_store.update(case)
        self._write_pg(updated, "update")
        return updated

    def _write_pg(self, case: CaseRecord, operation: str) -> None:
        try:
            if self.pg_store.available():
                self.pg_store.upsert(case)
                audit_event("case_engine", "dual_write_postgres", "ok", {"operacao": operation}, case.id)
            else:
                audit_event("case_engine", "dual_write_postgres", "erro", {"operacao": operation, "motivo": "postgres_indisponivel"}, case.id)
        except Exception as exc:
            audit_event("case_engine", "dual_write_postgres", "erro", {"operacao": operation, "erro": str(exc)}, case.id)
