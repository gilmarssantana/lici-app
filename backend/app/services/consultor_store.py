from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.consultor import ConsultorClienteRecord, ConsultorDemandaRecord
from app.services.audit_log import audit_event
from app.services.orgao_pg_store import PostgresConsultorStore


class JsonConsultorStore:
    def __init__(self, root: Path | str = "/root/lici-app/consultor"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.clientes_path = self.root / "clientes.json"
        self.demandas_path = self.root / "demandas.json"
        if not self.clientes_path.exists():
            self._write_json(self.clientes_path, [])
        if not self.demandas_path.exists():
            self._write_json(self.demandas_path, [])

    def list_clientes(self, organization_id: str | None = None) -> list[ConsultorClienteRecord]:
        items = self._read_clientes()
        if organization_id:
            items = [item for item in items if (item.organization_id or "default-org") == organization_id]
        return sorted(items, key=lambda item: item.atualizado_em, reverse=True)

    def get_cliente(self, cliente_id: str, organization_id: str | None = None) -> ConsultorClienteRecord | None:
        for cliente in self._read_clientes():
            if cliente.id == cliente_id and (organization_id is None or (cliente.organization_id or "default-org") == organization_id):
                return cliente
        return None

    def find_cliente(self, nome: str, documento: str = "", organization_id: str | None = None) -> ConsultorClienteRecord | None:
        nome_norm = self._norm(nome)
        doc_norm = self._only_digits(documento)
        for cliente in self._read_clientes():
            if organization_id and (cliente.organization_id or "default-org") != organization_id:
                continue
            if doc_norm and self._only_digits(cliente.documento) == doc_norm:
                return cliente
            if self._norm(cliente.nome) == nome_norm:
                return cliente
        return None

    def upsert_cliente(self, cliente: ConsultorClienteRecord) -> ConsultorClienteRecord:
        items = self._read_clientes()
        for idx, item in enumerate(items):
            if item.id == cliente.id:
                items[idx] = cliente
                self._write_clientes(items)
                return cliente
        items.append(cliente)
        self._write_clientes(items)
        return cliente

    def list_demandas(self, organization_id: str | None = None) -> list[ConsultorDemandaRecord]:
        items = self._read_demandas()
        if organization_id:
            items = [item for item in items if (item.organization_id or "default-org") == organization_id]
        return sorted(items, key=lambda item: item.atualizado_em, reverse=True)

    def get_demanda(self, demanda_id: str, organization_id: str | None = None) -> ConsultorDemandaRecord | None:
        for demanda in self._read_demandas():
            if demanda.id == demanda_id and (organization_id is None or (demanda.organization_id or "default-org") == organization_id):
                return demanda
        return None

    def demandas_cliente(self, cliente_id: str, organization_id: str | None = None) -> list[ConsultorDemandaRecord]:
        return [demanda for demanda in self.list_demandas(organization_id=organization_id) if demanda.cliente_id == cliente_id]

    def upsert_demanda(self, demanda: ConsultorDemandaRecord) -> ConsultorDemandaRecord:
        items = self._read_demandas()
        for idx, item in enumerate(items):
            if item.id == demanda.id:
                items[idx] = demanda
                self._write_demandas(items)
                return demanda
        items.append(demanda)
        self._write_demandas(items)
        return demanda

    def _read_clientes(self) -> list[ConsultorClienteRecord]:
        raw = json.loads(self.clientes_path.read_text(encoding="utf-8"))
        return [ConsultorClienteRecord(**item) for item in raw]

    def _read_demandas(self) -> list[ConsultorDemandaRecord]:
        raw = json.loads(self.demandas_path.read_text(encoding="utf-8"))
        return [ConsultorDemandaRecord(**item) for item in raw]

    def _write_clientes(self, items: list[ConsultorClienteRecord]) -> None:
        self._write_json(self.clientes_path, [item.model_dump() for item in items])

    def _write_demandas(self, items: list[ConsultorDemandaRecord]) -> None:
        self._write_json(self.demandas_path, [item.model_dump() for item in items])

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


class HybridConsultorStore:
    """Consultor dual-read/dual-write: PostgreSQL primeiro; JSON como fallback; JSON obrigatório na escrita."""

    def __init__(self, json_store: JsonConsultorStore | None = None, pg_store: PostgresConsultorStore | None = None):
        self.json_store = json_store or JsonConsultorStore()
        self.pg_store = pg_store or PostgresConsultorStore()

    def list_clientes(self, organization_id: str | None = None) -> list[ConsultorClienteRecord]:
        try:
            if self.pg_store.available():
                items = self.pg_store.list_clientes()
                if organization_id:
                    items = [item for item in items if (item.organization_id or "default-org") == organization_id]
                return items
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "list_clientes", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "list_clientes", "erro": str(exc)})
        return self.json_store.list_clientes(organization_id=organization_id)

    def get_cliente(self, cliente_id: str, organization_id: str | None = None) -> ConsultorClienteRecord | None:
        try:
            if self.pg_store.available():
                cliente = self.pg_store.get_cliente(cliente_id)
                if cliente and (organization_id is None or (cliente.organization_id or "default-org") == organization_id):
                    return cliente
                return None
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "get_cliente", "motivo": "postgres_indisponivel", "cliente_id": cliente_id}, cliente_id)
        except Exception as exc:
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "get_cliente", "cliente_id": cliente_id, "erro": str(exc)}, cliente_id)
        return self.json_store.get_cliente(cliente_id, organization_id=organization_id)

    def find_cliente(self, nome: str, documento: str = "", organization_id: str | None = None) -> ConsultorClienteRecord | None:
        try:
            if self.pg_store.available():
                cliente = self.pg_store.find_cliente(nome, documento)
                if cliente and (organization_id is None or (cliente.organization_id or "default-org") == organization_id):
                    return cliente
                return None
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "find_cliente", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "find_cliente", "erro": str(exc)})
        return self.json_store.find_cliente(nome, documento, organization_id=organization_id)

    def upsert_cliente(self, cliente: ConsultorClienteRecord) -> ConsultorClienteRecord:
        saved = self.json_store.upsert_cliente(cliente)
        try:
            if self.pg_store.available():
                self.pg_store.upsert_cliente(saved)
                audit_event("consultor_engine", "dual_write_postgres", "ok", {"operacao": "upsert_cliente"}, saved.id)
            else:
                audit_event("consultor_engine", "dual_write_postgres", "erro", {"operacao": "upsert_cliente", "motivo": "postgres_indisponivel"}, saved.id)
        except Exception as exc:
            audit_event("consultor_engine", "dual_write_postgres", "erro", {"operacao": "upsert_cliente", "erro": str(exc)}, saved.id)
        return saved

    def list_demandas(self, organization_id: str | None = None) -> list[ConsultorDemandaRecord]:
        try:
            if self.pg_store.available():
                items = self.pg_store.list_demandas()
                if organization_id:
                    items = [item for item in items if (item.organization_id or "default-org") == organization_id]
                return items
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "list_demandas", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "list_demandas", "erro": str(exc)})
        return self.json_store.list_demandas(organization_id=organization_id)

    def get_demanda(self, demanda_id: str, organization_id: str | None = None) -> ConsultorDemandaRecord | None:
        try:
            if self.pg_store.available():
                demanda = self.pg_store.get_demanda(demanda_id)
                if demanda and (organization_id is None or (demanda.organization_id or "default-org") == organization_id):
                    return demanda
                return None
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "get_demanda", "motivo": "postgres_indisponivel", "demanda_id": demanda_id}, demanda_id)
        except Exception as exc:
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "get_demanda", "demanda_id": demanda_id, "erro": str(exc)}, demanda_id)
        return self.json_store.get_demanda(demanda_id, organization_id=organization_id)

    def demandas_cliente(self, cliente_id: str, organization_id: str | None = None) -> list[ConsultorDemandaRecord]:
        try:
            if self.pg_store.available():
                items = self.pg_store.demandas_cliente(cliente_id)
                if organization_id:
                    items = [item for item in items if (item.organization_id or "default-org") == organization_id]
                return items
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "demandas_cliente", "motivo": "postgres_indisponivel", "cliente_id": cliente_id}, cliente_id)
        except Exception as exc:
            audit_event("consultor_engine", "postgres_fallback_json", "erro", {"operacao": "demandas_cliente", "cliente_id": cliente_id, "erro": str(exc)}, cliente_id)
        return self.json_store.demandas_cliente(cliente_id, organization_id=organization_id)

    def upsert_demanda(self, demanda: ConsultorDemandaRecord) -> ConsultorDemandaRecord:
        saved = self.json_store.upsert_demanda(demanda)
        try:
            if self.pg_store.available():
                self.pg_store.upsert_demanda(saved)
                audit_event("consultor_engine", "dual_write_postgres", "ok", {"operacao": "upsert_demanda"}, saved.id)
            else:
                audit_event("consultor_engine", "dual_write_postgres", "erro", {"operacao": "upsert_demanda", "motivo": "postgres_indisponivel"}, saved.id)
        except Exception as exc:
            audit_event("consultor_engine", "dual_write_postgres", "erro", {"operacao": "upsert_demanda", "erro": str(exc)}, saved.id)
        return saved
