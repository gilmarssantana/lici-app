from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.consultor import ConsultorClienteRecord, ConsultorDemandaRecord
from app.schemas.orgao import OrgaoEvent, OrgaoRecord
from app.services.orgao_pg_store import PostgresConsultorStore, PostgresOrgaoStore


def create_schema() -> None:
    store = PostgresOrgaoStore()
    if not store.dsn:
        raise RuntimeError("LICI_DATABASE_URL não configurado")
    import psycopg

    with psycopg.connect(store.dsn, connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS orgaos (
                  id text PRIMARY KEY,
                  name text NOT NULL,
                  cnpj text,
                  uf text,
                  esfera text,
                  risk text,
                  behavior text,
                  reliability_score integer,
                  opportunity_score integer,
                  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz,
                  updated_at timestamptz
                );
                CREATE INDEX IF NOT EXISTS idx_orgaos_name ON orgaos (name);
                CREATE INDEX IF NOT EXISTS idx_orgaos_cnpj ON orgaos (cnpj);
                CREATE INDEX IF NOT EXISTS idx_orgaos_uf_risk ON orgaos (uf, risk);

                CREATE TABLE IF NOT EXISTS orgao_events (
                  id text PRIMARY KEY,
                  orgao_id text NOT NULL,
                  event_type text,
                  description text,
                  impact text,
                  case_id text,
                  radar_id text,
                  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz
                );
                CREATE INDEX IF NOT EXISTS idx_orgao_events_orgao_id ON orgao_events (orgao_id);
                CREATE INDEX IF NOT EXISTS idx_orgao_events_type ON orgao_events (event_type);
                CREATE INDEX IF NOT EXISTS idx_orgao_events_created_at ON orgao_events (created_at);

                CREATE TABLE IF NOT EXISTS consultor_clientes (
                  id text PRIMARY KEY,
                  name text NOT NULL,
                  document text,
                  segment text,
                  uf text,
                  status text,
                  potential_score integer,
                  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz,
                  updated_at timestamptz
                );
                CREATE INDEX IF NOT EXISTS idx_consultor_clientes_name ON consultor_clientes (name);
                CREATE INDEX IF NOT EXISTS idx_consultor_clientes_document ON consultor_clientes (document);
                CREATE INDEX IF NOT EXISTS idx_consultor_clientes_status ON consultor_clientes (status);

                CREATE TABLE IF NOT EXISTS consultor_demandas (
                  id text PRIMARY KEY,
                  cliente_id text NOT NULL,
                  client_name text,
                  demand_type text,
                  description text,
                  deadline text,
                  priority text,
                  status text,
                  case_id text,
                  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz,
                  updated_at timestamptz
                );
                CREATE INDEX IF NOT EXISTS idx_consultor_demandas_cliente_id ON consultor_demandas (cliente_id);
                CREATE INDEX IF NOT EXISTS idx_consultor_demandas_status_priority ON consultor_demandas (status, priority);
                CREATE INDEX IF NOT EXISTS idx_consultor_demandas_type ON consultor_demandas (demand_type);
                """
            )


def _load(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def migrate() -> dict[str, int]:
    create_schema()
    orgao_store = PostgresOrgaoStore()
    consultor_store = PostgresConsultorStore()
    counts = {"orgaos": 0, "orgao_events": 0, "consultor_clientes": 0, "consultor_demandas": 0}

    for raw in _load("/root/lici-app/orgaos/orgaos.json"):
        orgao_store.upsert(OrgaoRecord(**raw))
        counts["orgaos"] += 1
    for raw in _load("/root/lici-app/orgaos/historico.json"):
        orgao_store.add_event(OrgaoEvent(**raw))
        counts["orgao_events"] += 1
    for raw in _load("/root/lici-app/consultor/clientes.json"):
        consultor_store.upsert_cliente(ConsultorClienteRecord(**raw))
        counts["consultor_clientes"] += 1
    for raw in _load("/root/lici-app/consultor/demandas.json"):
        consultor_store.upsert_demanda(ConsultorDemandaRecord(**raw))
        counts["consultor_demandas"] += 1
    return counts


if __name__ == "__main__":
    print(json.dumps(migrate(), ensure_ascii=False, indent=2))
