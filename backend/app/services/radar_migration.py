from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.alert import AlertGenerateLog, AlertRecord
from app.schemas.radar import RadarOpportunity
from app.schemas.triage import TriageItem, TriageRunLog
from app.services.radar_pg_store import PostgresAlertStore, PostgresRadarStore, PostgresTriageStore


def create_schema() -> None:
    store = PostgresRadarStore()
    if not store.dsn:
        raise RuntimeError("LICI_DATABASE_URL não configurado")
    import psycopg
    with psycopg.connect(store.dsn, connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS radar_opportunities (
                  id text PRIMARY KEY,
                  source text NOT NULL DEFAULT 'PNCP',
                  external_id text,
                  orgao_name text,
                  unit_name text,
                  uf text,
                  object text,
                  modality text,
                  estimated_value numeric,
                  publication_date text,
                  opening_date text,
                  proposal_deadline text,
                  link text,
                  preliminary_score integer,
                  triage_classification text,
                  status text,
                  case_id text,
                  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz,
                  updated_at timestamptz
                );
                CREATE INDEX IF NOT EXISTS idx_radar_opportunities_external_id ON radar_opportunities (external_id);
                CREATE INDEX IF NOT EXISTS idx_radar_opportunities_deadline ON radar_opportunities (proposal_deadline);
                CREATE INDEX IF NOT EXISTS idx_radar_opportunities_status ON radar_opportunities (triage_classification, status);

                CREATE TABLE IF NOT EXISTS triage_items (
                  id text PRIMARY KEY,
                  record_type text NOT NULL DEFAULT 'item',
                  opportunity_id text,
                  external_id text,
                  orgao_name text,
                  uf text,
                  object text,
                  modality text,
                  estimated_value numeric,
                  proposal_deadline text,
                  preliminary_score integer,
                  classification text,
                  status text,
                  recommended_action text,
                  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz,
                  updated_at timestamptz
                );
                CREATE INDEX IF NOT EXISTS idx_triage_items_status_classification ON triage_items (status, classification);
                CREATE INDEX IF NOT EXISTS idx_triage_items_opportunity_id ON triage_items (opportunity_id);
                CREATE INDEX IF NOT EXISTS idx_triage_items_record_type ON triage_items (record_type);

                CREATE TABLE IF NOT EXISTS alerts (
                  id text PRIMARY KEY,
                  record_type text NOT NULL DEFAULT 'alert',
                  alert_key text,
                  title text,
                  severity text,
                  source text,
                  reference_id text,
                  orgao_name text,
                  object text,
                  read boolean NOT NULL DEFAULT false,
                  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz,
                  updated_at timestamptz
                );
                CREATE INDEX IF NOT EXISTS idx_alerts_read_severity ON alerts (read, severity);
                CREATE INDEX IF NOT EXISTS idx_alerts_reference_id ON alerts (reference_id);
                CREATE INDEX IF NOT EXISTS idx_alerts_record_type ON alerts (record_type);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_alerts_key_unique ON alerts (alert_key) WHERE record_type = 'alert' AND alert_key IS NOT NULL;
                """
            )


def _load(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def migrate() -> dict[str, int]:
    create_schema()
    radar_store = PostgresRadarStore()
    triage_store = PostgresTriageStore()
    alert_store = PostgresAlertStore()
    counts = {"radar_opportunities": 0, "triage_items": 0, "triage_logs": 0, "alerts": 0, "alert_logs": 0}

    for raw in _load("/root/lici-app/radar/oportunidades.json"):
        radar_store.upsert(RadarOpportunity(**raw))
        counts["radar_opportunities"] += 1
    for raw in _load("/root/lici-app/triagem/fila.json"):
        triage_store.upsert_item(TriageItem(**raw))
        counts["triage_items"] += 1
    for raw in _load("/root/lici-app/triagem/logs.json"):
        triage_store.append_log(TriageRunLog(**raw))
        counts["triage_logs"] += 1
    for raw in _load("/root/lici-app/alertas/alertas.json"):
        alert_store.upsert_alert(AlertRecord(**raw))
        counts["alerts"] += 1
    for raw in _load("/root/lici-app/alertas/logs.json"):
        alert_store.append_log(AlertGenerateLog(**raw))
        counts["alert_logs"] += 1
    return counts


if __name__ == "__main__":
    print(json.dumps(migrate(), ensure_ascii=False, indent=2))
