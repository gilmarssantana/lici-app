from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.schemas.consultor import ConsultorClienteRecord, ConsultorDemandaRecord
from app.schemas.orgao import OrgaoEvent, OrgaoRecord

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

POSTGRES_ENV_FILE = Path("/root/lici-app/secrets/postgres.env")


class _BasePostgresStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.getenv("LICI_DATABASE_URL") or self._dsn_from_env_file()

    def available(self) -> bool:
        if not psycopg or not self.dsn:
            return False
        try:
            with psycopg.connect(self.dsn, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True
        except Exception:
            return False

    def _connect(self):
        if not psycopg or not self.dsn:
            raise RuntimeError("PostgreSQL indisponível")
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3)

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith("LICI_DATABASE_URL="):
                    return line.split("=", 1)[1].strip()
        except FileNotFoundError:
            return None
        return None

    def _raw(self, raw: Any) -> dict[str, Any]:
        if raw is None:
            return {}
        if isinstance(raw, str):
            return json.loads(raw)
        return raw


class PostgresOrgaoStore(_BasePostgresStore):
    def list(self) -> list[OrgaoRecord]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM orgaos ORDER BY updated_at DESC NULLS LAST, created_at DESC")
                return [OrgaoRecord(**self._raw(row["raw_payload"])) for row in cur.fetchall()]

    def get(self, orgao_id: str) -> OrgaoRecord | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM orgaos WHERE id = %s", (orgao_id,))
                row = cur.fetchone()
                return OrgaoRecord(**self._raw(row["raw_payload"])) if row else None

    def find_by_nome_cnpj(self, nome: str, cnpj: str = "") -> OrgaoRecord | None:
        cnpj_digits = "".join(ch for ch in (cnpj or "") if ch.isdigit())
        nome_norm = " ".join((nome or "").strip().lower().split())
        for item in self.list():
            if cnpj_digits and "".join(ch for ch in item.cnpj if ch.isdigit()) == cnpj_digits:
                return item
            if " ".join(item.nome.strip().lower().split()) == nome_norm:
                return item
        return None

    def upsert(self, orgao: OrgaoRecord) -> OrgaoRecord:
        raw = orgao.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO orgaos (
                      id, name, cnpj, uf, esfera, risk, behavior, reliability_score, opportunity_score,
                      raw_payload, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      name=EXCLUDED.name, cnpj=EXCLUDED.cnpj, uf=EXCLUDED.uf, esfera=EXCLUDED.esfera,
                      risk=EXCLUDED.risk, behavior=EXCLUDED.behavior, reliability_score=EXCLUDED.reliability_score,
                      opportunity_score=EXCLUDED.opportunity_score, raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at
                    """,
                    (
                        orgao.id,
                        orgao.nome,
                        orgao.cnpj,
                        orgao.uf,
                        orgao.esfera,
                        orgao.risco,
                        orgao.comportamento,
                        orgao.score_confiabilidade,
                        orgao.score_oportunidade,
                        json.dumps(raw, ensure_ascii=False, default=str),
                        orgao.criado_em,
                        orgao.atualizado_em,
                    ),
                )
        return orgao

    def add_event(self, event: OrgaoEvent) -> OrgaoEvent:
        raw = event.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO orgao_events (id, orgao_id, event_type, description, impact, case_id, radar_id, raw_payload, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      orgao_id=EXCLUDED.orgao_id, event_type=EXCLUDED.event_type, description=EXCLUDED.description,
                      impact=EXCLUDED.impact, case_id=EXCLUDED.case_id, radar_id=EXCLUDED.radar_id,
                      raw_payload=EXCLUDED.raw_payload, created_at=EXCLUDED.created_at
                    """,
                    (event.id, event.orgao_id, event.tipo, event.descricao, event.impacto, event.caso_id, event.radar_id, json.dumps(raw, ensure_ascii=False, default=str), event.data),
                )
        return event

    def history(self, orgao_id: str) -> list[OrgaoEvent]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM orgao_events WHERE orgao_id = %s ORDER BY created_at DESC", (orgao_id,))
                return [OrgaoEvent(**self._raw(row["raw_payload"])) for row in cur.fetchall()]


class PostgresConsultorStore(_BasePostgresStore):
    def list_clientes(self) -> list[ConsultorClienteRecord]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM consultor_clientes ORDER BY updated_at DESC NULLS LAST, created_at DESC")
                return [ConsultorClienteRecord(**self._raw(row["raw_payload"])) for row in cur.fetchall()]

    def get_cliente(self, cliente_id: str) -> ConsultorClienteRecord | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM consultor_clientes WHERE id = %s", (cliente_id,))
                row = cur.fetchone()
                return ConsultorClienteRecord(**self._raw(row["raw_payload"])) if row else None

    def find_cliente(self, nome: str, documento: str = "") -> ConsultorClienteRecord | None:
        doc_digits = "".join(ch for ch in (documento or "") if ch.isdigit())
        nome_norm = " ".join((nome or "").strip().lower().split())
        for item in self.list_clientes():
            if doc_digits and "".join(ch for ch in item.documento if ch.isdigit()) == doc_digits:
                return item
            if " ".join(item.nome.strip().lower().split()) == nome_norm:
                return item
        return None

    def upsert_cliente(self, cliente: ConsultorClienteRecord) -> ConsultorClienteRecord:
        raw = cliente.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO consultor_clientes (id, name, document, segment, uf, status, potential_score, raw_payload, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      name=EXCLUDED.name, document=EXCLUDED.document, segment=EXCLUDED.segment, uf=EXCLUDED.uf,
                      status=EXCLUDED.status, potential_score=EXCLUDED.potential_score,
                      raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at
                    """,
                    (cliente.id, cliente.nome, cliente.documento, cliente.segmento, cliente.uf, cliente.status, cliente.score_potencial, json.dumps(raw, ensure_ascii=False, default=str), cliente.criado_em, cliente.atualizado_em),
                )
        return cliente

    def list_demandas(self) -> list[ConsultorDemandaRecord]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM consultor_demandas ORDER BY updated_at DESC NULLS LAST, created_at DESC")
                return [ConsultorDemandaRecord(**self._raw(row["raw_payload"])) for row in cur.fetchall()]

    def get_demanda(self, demanda_id: str) -> ConsultorDemandaRecord | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM consultor_demandas WHERE id = %s", (demanda_id,))
                row = cur.fetchone()
                return ConsultorDemandaRecord(**self._raw(row["raw_payload"])) if row else None

    def demandas_cliente(self, cliente_id: str) -> list[ConsultorDemandaRecord]:
        return [demanda for demanda in self.list_demandas() if demanda.cliente_id == cliente_id]

    def upsert_demanda(self, demanda: ConsultorDemandaRecord) -> ConsultorDemandaRecord:
        raw = demanda.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO consultor_demandas (
                      id, cliente_id, client_name, demand_type, description, deadline, priority, status, case_id,
                      raw_payload, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      cliente_id=EXCLUDED.cliente_id, client_name=EXCLUDED.client_name, demand_type=EXCLUDED.demand_type,
                      description=EXCLUDED.description, deadline=EXCLUDED.deadline, priority=EXCLUDED.priority,
                      status=EXCLUDED.status, case_id=EXCLUDED.case_id, raw_payload=EXCLUDED.raw_payload,
                      updated_at=EXCLUDED.updated_at
                    """,
                    (demanda.id, demanda.cliente_id, demanda.cliente_nome, demanda.tipo, demanda.descricao, demanda.prazo, demanda.prioridade, demanda.status, demanda.caso_vivo_id, json.dumps(raw, ensure_ascii=False, default=str), demanda.criado_em, demanda.atualizado_em),
                )
        return demanda
