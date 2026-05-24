from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.schemas.concorrente import ConcorrenteEvent, ConcorrenteRecord

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

POSTGRES_ENV_FILE = Path('/root/lici-app/secrets/postgres.env')


class PostgresConcorrenteStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.getenv('LICI_DATABASE_URL') or self._dsn_from_env_file()

    def available(self) -> bool:
        if not psycopg or not self.dsn:
            return False
        try:
            self.ensure_schema()
            return True
        except Exception:
            return False

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS competitors (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        cnpj TEXT,
                        segment TEXT,
                        uf TEXT,
                        operational_risk TEXT,
                        risk_score INTEGER,
                        competitiveness_score INTEGER,
                        frequency INTEGER,
                        wins INTEGER,
                        losses INTEGER,
                        raw_payload JSONB,
                        created_at TIMESTAMPTZ,
                        updated_at TIMESTAMPTZ
                    )
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS competitor_events (
                        id TEXT PRIMARY KEY,
                        competitor_id TEXT,
                        event_type TEXT,
                        description TEXT,
                        orgao TEXT,
                        case_id TEXT,
                        radar_id TEXT,
                        proposal_value NUMERIC,
                        impact TEXT,
                        raw_payload JSONB,
                        created_at TIMESTAMPTZ
                    )
                ''')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_competitors_name ON competitors (name)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_competitor_events_competitor ON competitor_events (competitor_id)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_competitor_events_type ON competitor_events (event_type)')

    def list(self) -> list[ConcorrenteRecord]:
        self.ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT raw_payload FROM competitors ORDER BY updated_at DESC NULLS LAST, created_at DESC')
                return [ConcorrenteRecord(**self._raw(row['raw_payload'])) for row in cur.fetchall()]

    def get(self, concorrente_id: str) -> ConcorrenteRecord | None:
        self.ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT raw_payload FROM competitors WHERE id = %s', (concorrente_id,))
                row = cur.fetchone()
                return ConcorrenteRecord(**self._raw(row['raw_payload'])) if row else None

    def find_by_nome_cnpj(self, nome: str, cnpj: str = '') -> ConcorrenteRecord | None:
        cnpj_digits = ''.join(ch for ch in (cnpj or '') if ch.isdigit())
        nome_norm = ' '.join((nome or '').strip().lower().split())
        for item in self.list():
            if cnpj_digits and ''.join(ch for ch in item.cnpj if ch.isdigit()) == cnpj_digits:
                return item
            if ' '.join(item.nome.strip().lower().split()) == nome_norm:
                return item
        return None

    def upsert(self, concorrente: ConcorrenteRecord) -> ConcorrenteRecord:
        self.ensure_schema()
        raw = concorrente.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO competitors (id,name,cnpj,segment,uf,operational_risk,risk_score,competitiveness_score,frequency,wins,losses,raw_payload,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      name=EXCLUDED.name, cnpj=EXCLUDED.cnpj, segment=EXCLUDED.segment, uf=EXCLUDED.uf,
                      operational_risk=EXCLUDED.operational_risk, risk_score=EXCLUDED.risk_score,
                      competitiveness_score=EXCLUDED.competitiveness_score, frequency=EXCLUDED.frequency,
                      wins=EXCLUDED.wins, losses=EXCLUDED.losses, raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at
                ''', (concorrente.id, concorrente.nome, concorrente.cnpj, concorrente.segmento, concorrente.uf, concorrente.risco_operacional, concorrente.score_risco, concorrente.score_competitividade, concorrente.frequencia, concorrente.vitorias, concorrente.derrotas, json.dumps(raw, ensure_ascii=False, default=str), concorrente.criado_em, concorrente.atualizado_em))
        return concorrente

    def add_event(self, event: ConcorrenteEvent) -> ConcorrenteEvent:
        self.ensure_schema()
        raw = event.model_dump()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO competitor_events (id,competitor_id,event_type,description,orgao,case_id,radar_id,proposal_value,impact,raw_payload,created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                    ON CONFLICT (id) DO UPDATE SET competitor_id=EXCLUDED.competitor_id, event_type=EXCLUDED.event_type,
                      description=EXCLUDED.description, orgao=EXCLUDED.orgao, case_id=EXCLUDED.case_id, radar_id=EXCLUDED.radar_id,
                      proposal_value=EXCLUDED.proposal_value, impact=EXCLUDED.impact, raw_payload=EXCLUDED.raw_payload, created_at=EXCLUDED.created_at
                ''', (event.id, event.concorrente_id, event.tipo, event.descricao, event.orgao, event.caso_id, event.radar_id, event.valor_proposta, event.impacto, json.dumps(raw, ensure_ascii=False, default=str), event.data))
        return event

    def history(self, concorrente_id: str) -> list[ConcorrenteEvent]:
        self.ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT raw_payload FROM competitor_events WHERE competitor_id = %s ORDER BY created_at DESC', (concorrente_id,))
                return [ConcorrenteEvent(**self._raw(row['raw_payload'])) for row in cur.fetchall()]

    def events(self) -> list[ConcorrenteEvent]:
        self.ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT raw_payload FROM competitor_events ORDER BY created_at DESC')
                return [ConcorrenteEvent(**self._raw(row['raw_payload'])) for row in cur.fetchall()]

    def _connect(self):
        if not psycopg or not self.dsn:
            raise RuntimeError('PostgreSQL indisponível')
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3)

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding='utf-8').splitlines():
                if line.startswith('LICI_DATABASE_URL='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
        except FileNotFoundError:
            return None
        return None

    def _raw(self, raw: Any) -> dict[str, Any]:
        if raw is None:
            return {}
        if isinstance(raw, str):
            return json.loads(raw)
        return raw
