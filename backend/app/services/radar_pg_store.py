from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.schemas.alert import AlertGenerateLog, AlertRecord
from app.schemas.radar import RadarOpportunity
from app.schemas.triage import TriageItem, TriageRunLog

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


class PostgresRadarStore(_BasePostgresStore):
    def list(self) -> list[RadarOpportunity]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM radar_opportunities ORDER BY updated_at DESC NULLS LAST, created_at DESC")
                return [RadarOpportunity(**self._raw(row["raw_payload"])) for row in cur.fetchall()]

    def get(self, opportunity_id: str) -> RadarOpportunity | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM radar_opportunities WHERE id = %s", (opportunity_id,))
                row = cur.fetchone()
                return RadarOpportunity(**self._raw(row["raw_payload"])) if row else None

    def upsert(self, opportunity: RadarOpportunity) -> RadarOpportunity:
        raw = opportunity.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO radar_opportunities (
                      id, source, external_id, orgao_name, unit_name, uf, object, modality,
                      estimated_value, publication_date, opening_date, proposal_deadline, link,
                      preliminary_score, triage_classification, status, case_id, raw_payload, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      source=EXCLUDED.source, external_id=EXCLUDED.external_id, orgao_name=EXCLUDED.orgao_name,
                      unit_name=EXCLUDED.unit_name, uf=EXCLUDED.uf, object=EXCLUDED.object, modality=EXCLUDED.modality,
                      estimated_value=EXCLUDED.estimated_value, publication_date=EXCLUDED.publication_date,
                      opening_date=EXCLUDED.opening_date, proposal_deadline=EXCLUDED.proposal_deadline, link=EXCLUDED.link,
                      preliminary_score=EXCLUDED.preliminary_score, triage_classification=EXCLUDED.triage_classification,
                      status=EXCLUDED.status, case_id=EXCLUDED.case_id, raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at
                    """,
                    (
                        opportunity.id, opportunity.fonte, opportunity.pncp_id, opportunity.orgao, opportunity.unidade,
                        opportunity.uf, opportunity.objeto, opportunity.modalidade, opportunity.valor_estimado,
                        opportunity.data_publicacao or None, opportunity.data_abertura or None, opportunity.data_encerramento or None,
                        opportunity.link, opportunity.score_preliminar, None, "capturada", opportunity.caso_id,
                        json.dumps(raw, ensure_ascii=False, default=str), opportunity.criado_em, opportunity.atualizado_em,
                    ),
                )
        return opportunity

    def upsert_many(self, opportunities: list[RadarOpportunity]) -> list[RadarOpportunity]:
        for item in opportunities:
            self.upsert(item)
        return opportunities


class PostgresTriageStore(_BasePostgresStore):
    def list_queue(self) -> list[TriageItem]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM triage_items WHERE record_type = 'item' ORDER BY updated_at DESC NULLS LAST, created_at DESC")
                return [TriageItem(**self._raw(row["raw_payload"])) for row in cur.fetchall()]

    def write_queue(self, items: list[TriageItem]) -> list[TriageItem]:
        for item in items:
            self.upsert_item(item)
        return items

    def get_item(self, opportunity_id: str) -> TriageItem | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM triage_items WHERE record_type = 'item' AND (id = %s OR opportunity_id = %s)", (opportunity_id, opportunity_id))
                row = cur.fetchone()
                return TriageItem(**self._raw(row["raw_payload"])) if row else None

    def update_item(self, item: TriageItem) -> TriageItem:
        return self.upsert_item(item)

    def upsert_item(self, item: TriageItem) -> TriageItem:
        raw = item.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO triage_items (
                      id, record_type, opportunity_id, external_id, orgao_name, uf, object, modality, estimated_value,
                      proposal_deadline, preliminary_score, classification, status, recommended_action,
                      raw_payload, created_at, updated_at
                    ) VALUES (%s,'item',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      opportunity_id=EXCLUDED.opportunity_id, external_id=EXCLUDED.external_id, orgao_name=EXCLUDED.orgao_name,
                      uf=EXCLUDED.uf, object=EXCLUDED.object, modality=EXCLUDED.modality, estimated_value=EXCLUDED.estimated_value,
                      proposal_deadline=EXCLUDED.proposal_deadline, preliminary_score=EXCLUDED.preliminary_score,
                      classification=EXCLUDED.classification, status=EXCLUDED.status, recommended_action=EXCLUDED.recommended_action,
                      raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at
                    """,
                    (
                        item.id, item.oportunidade_id, item.pncp_id, item.orgao, item.uf, item.objeto, item.modalidade,
                        item.valor_estimado, item.data_encerramento or None, item.score_preliminar, item.classificacao,
                        item.status, item.acao_recomendada, json.dumps(raw, ensure_ascii=False, default=str), item.criado_em, item.atualizado_em,
                    ),
                )
        return item

    def list_logs(self) -> list[TriageRunLog]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM triage_items WHERE record_type = 'log' ORDER BY created_at DESC")
                return [TriageRunLog(**self._raw(row["raw_payload"])) for row in cur.fetchall()]

    def append_log(self, log: TriageRunLog) -> TriageRunLog:
        raw = log.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO triage_items (id, record_type, status, raw_payload, created_at, updated_at)
                    VALUES (%s,'log',%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status, raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at
                    """,
                    (log.id, log.status, json.dumps(raw, ensure_ascii=False, default=str), log.iniciado_em, log.finalizado_em or log.iniciado_em),
                )
        return log


class PostgresAlertStore(_BasePostgresStore):
    def list_alerts(self) -> list[AlertRecord]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM alerts WHERE record_type = 'alert' ORDER BY updated_at DESC NULLS LAST, created_at DESC")
                return [AlertRecord(**self._raw(row["raw_payload"])) for row in cur.fetchall()]

    def write_alerts(self, alerts: list[AlertRecord]) -> list[AlertRecord]:
        for alert in alerts:
            self.upsert_alert(alert)
        return alerts

    def upsert_many(self, incoming: list[AlertRecord]) -> tuple[list[AlertRecord], int, int]:
        existing = self.list_alerts()
        by_key = {item.chave: item for item in existing}
        novos = 0
        atualizados = 0
        saved: list[AlertRecord] = []
        for alert in incoming:
            current = by_key.get(alert.chave)
            if current:
                alert.id = current.id
                alert.criado_em = current.criado_em
                alert.lido = current.lido
                atualizados += 1
            else:
                novos += 1
            self.upsert_alert(alert)
            saved.append(alert)
        return saved, novos, atualizados

    def get(self, alert_id: str) -> AlertRecord | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM alerts WHERE record_type = 'alert' AND id = %s", (alert_id,))
                row = cur.fetchone()
                return AlertRecord(**self._raw(row["raw_payload"])) if row else None

    def update(self, alert: AlertRecord) -> AlertRecord:
        return self.upsert_alert(alert)

    def upsert_alert(self, alert: AlertRecord) -> AlertRecord:
        raw = alert.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO alerts (
                      id, record_type, alert_key, title, severity, source, reference_id, orgao_name, object,
                      read, raw_payload, created_at, updated_at
                    ) VALUES (%s,'alert',%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      alert_key=EXCLUDED.alert_key, title=EXCLUDED.title, severity=EXCLUDED.severity,
                      source=EXCLUDED.source, reference_id=EXCLUDED.reference_id, orgao_name=EXCLUDED.orgao_name,
                      object=EXCLUDED.object, read=EXCLUDED.read, raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at
                    """,
                    (
                        alert.id, alert.chave, alert.titulo, alert.severidade, alert.fonte, alert.referencia_id,
                        alert.orgao, alert.objeto, alert.lido, json.dumps(raw, ensure_ascii=False, default=str), alert.criado_em, alert.atualizado_em,
                    ),
                )
        return alert

    def list_logs(self) -> list[AlertGenerateLog]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM alerts WHERE record_type = 'log' ORDER BY created_at DESC")
                return [AlertGenerateLog(**self._raw(row["raw_payload"])) for row in cur.fetchall()]

    def append_log(self, log: AlertGenerateLog) -> AlertGenerateLog:
        raw = log.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO alerts (id, record_type, severity, read, raw_payload, created_at, updated_at)
                    VALUES (%s,'log',%s,false,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET severity=EXCLUDED.severity, raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at
                    """,
                    (log.id, log.status, json.dumps(raw, ensure_ascii=False, default=str), log.iniciado_em, log.finalizado_em or log.iniciado_em),
                )
        return log
