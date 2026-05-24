from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.orgao import OrgaoEvent, OrgaoRecord
from app.services.audit_log import audit_event
from app.services.orgao_pg_store import PostgresOrgaoStore


class JsonOrgaoStore:
    def __init__(self, root: Path | str = "/root/lici-app/orgaos"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.orgaos_path = self.root / "orgaos.json"
        self.historico_path = self.root / "historico.json"
        if not self.orgaos_path.exists():
            self._write_json(self.orgaos_path, [])
        if not self.historico_path.exists():
            self._write_json(self.historico_path, [])

    def list(self, organization_id: str | None = None) -> list[OrgaoRecord]:
        items = self._read_orgaos()
        if organization_id:
            items = [item for item in items if (item.organization_id or "default-org") == organization_id]
        return sorted(items, key=lambda item: item.atualizado_em, reverse=True)

    def get(self, orgao_id: str, organization_id: str | None = None) -> OrgaoRecord | None:
        for orgao in self._read_orgaos():
            if orgao.id == orgao_id and (organization_id is None or (orgao.organization_id or "default-org") == organization_id):
                return orgao
        return None

    def find_by_nome_cnpj(self, nome: str, cnpj: str = "") -> OrgaoRecord | None:
        nome_norm = self._norm(nome)
        cnpj_norm = self._only_digits(cnpj)
        for orgao in self._read_orgaos():
            if cnpj_norm and self._only_digits(orgao.cnpj) == cnpj_norm:
                return orgao
            if self._norm(orgao.nome) == nome_norm:
                return orgao
        return None

    def upsert(self, orgao: OrgaoRecord) -> OrgaoRecord:
        items = self._read_orgaos()
        for idx, item in enumerate(items):
            if item.id == orgao.id:
                items[idx] = orgao
                self._write_orgaos(items)
                return orgao
        items.append(orgao)
        self._write_orgaos(items)
        return orgao

    def add_event(self, event: OrgaoEvent) -> OrgaoEvent:
        eventos = self._read_eventos()
        eventos.append(event)
        self._write_eventos(eventos)
        return event

    def history(self, orgao_id: str) -> list[OrgaoEvent]:
        eventos = [event for event in self._read_eventos() if event.orgao_id == orgao_id]
        return sorted(eventos, key=lambda item: item.data, reverse=True)

    def _read_orgaos(self) -> list[OrgaoRecord]:
        raw = json.loads(self.orgaos_path.read_text(encoding="utf-8"))
        return [OrgaoRecord(**item) for item in raw]

    def _read_eventos(self) -> list[OrgaoEvent]:
        raw = json.loads(self.historico_path.read_text(encoding="utf-8"))
        return [OrgaoEvent(**item) for item in raw]

    def _write_orgaos(self, items: list[OrgaoRecord]) -> None:
        self._write_json(self.orgaos_path, [item.model_dump() for item in items])

    def _write_eventos(self, items: list[OrgaoEvent]) -> None:
        self._write_json(self.historico_path, [item.model_dump() for item in items])

    def _write_json(self, path: Path, data: list[dict]) -> None:
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.root, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)

    def _norm(self, value: str) -> str:
        return " ".join((value or "").strip().lower().split())

    def _only_digits(self, value: str) -> str:
        return "".join(ch for ch in (value or "") if ch.isdigit())


class HybridOrgaoStore:
    """Órgãos dual-read/dual-write: PostgreSQL primeiro; JSON como fallback; JSON obrigatório na escrita."""

    def __init__(self, json_store: JsonOrgaoStore | None = None, pg_store: PostgresOrgaoStore | None = None):
        self.json_store = json_store or JsonOrgaoStore()
        self.pg_store = pg_store or PostgresOrgaoStore()

    def list(self, organization_id: str | None = None) -> list[OrgaoRecord]:
        try:
            if self.pg_store.available():
                items = self.pg_store.list()
                if organization_id:
                    items = [item for item in items if (item.organization_id or "default-org") == organization_id]
                return items
            audit_event("orgaos_engine", "postgres_fallback_json", "erro", {"operacao": "list", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("orgaos_engine", "postgres_fallback_json", "erro", {"operacao": "list", "erro": str(exc)})
        return self.json_store.list(organization_id=organization_id)

    def get(self, orgao_id: str, organization_id: str | None = None) -> OrgaoRecord | None:
        try:
            if self.pg_store.available():
                orgao = self.pg_store.get(orgao_id)
                if orgao and (organization_id is None or (orgao.organization_id or "default-org") == organization_id):
                    return orgao
                return None
            audit_event("orgaos_engine", "postgres_fallback_json", "erro", {"operacao": "get", "motivo": "postgres_indisponivel", "orgao_id": orgao_id}, orgao_id)
        except Exception as exc:
            audit_event("orgaos_engine", "postgres_fallback_json", "erro", {"operacao": "get", "orgao_id": orgao_id, "erro": str(exc)}, orgao_id)
        return self.json_store.get(orgao_id, organization_id=organization_id)

    def find_by_nome_cnpj(self, nome: str, cnpj: str = "") -> OrgaoRecord | None:
        try:
            if self.pg_store.available():
                return self.pg_store.find_by_nome_cnpj(nome, cnpj)
            audit_event("orgaos_engine", "postgres_fallback_json", "erro", {"operacao": "find_by_nome_cnpj", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("orgaos_engine", "postgres_fallback_json", "erro", {"operacao": "find_by_nome_cnpj", "erro": str(exc)})
        return self.json_store.find_by_nome_cnpj(nome, cnpj)

    def upsert(self, orgao: OrgaoRecord) -> OrgaoRecord:
        saved = self.json_store.upsert(orgao)
        try:
            if self.pg_store.available():
                self.pg_store.upsert(saved)
                audit_event("orgaos_engine", "dual_write_postgres", "ok", {"operacao": "upsert"}, saved.id)
            else:
                audit_event("orgaos_engine", "dual_write_postgres", "erro", {"operacao": "upsert", "motivo": "postgres_indisponivel"}, saved.id)
        except Exception as exc:
            audit_event("orgaos_engine", "dual_write_postgres", "erro", {"operacao": "upsert", "erro": str(exc)}, saved.id)
        return saved

    def add_event(self, event: OrgaoEvent) -> OrgaoEvent:
        saved = self.json_store.add_event(event)
        try:
            if self.pg_store.available():
                self.pg_store.add_event(saved)
                audit_event("orgaos_engine", "dual_write_postgres", "ok", {"operacao": "add_event"}, saved.id)
            else:
                audit_event("orgaos_engine", "dual_write_postgres", "erro", {"operacao": "add_event", "motivo": "postgres_indisponivel"}, saved.id)
        except Exception as exc:
            audit_event("orgaos_engine", "dual_write_postgres", "erro", {"operacao": "add_event", "erro": str(exc)}, saved.id)
        return saved

    def history(self, orgao_id: str) -> list[OrgaoEvent]:
        try:
            if self.pg_store.available():
                return self.pg_store.history(orgao_id)
            audit_event("orgaos_engine", "postgres_fallback_json", "erro", {"operacao": "history", "motivo": "postgres_indisponivel", "orgao_id": orgao_id}, orgao_id)
        except Exception as exc:
            audit_event("orgaos_engine", "postgres_fallback_json", "erro", {"operacao": "history", "orgao_id": orgao_id, "erro": str(exc)}, orgao_id)
        return self.json_store.history(orgao_id)
