from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.schemas.case import CaseEvent, CaseRecord

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

POSTGRES_ENV_FILE = Path("/root/lici-app/secrets/postgres.env")


class PostgresCaseStore:
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

    def create(self, case: CaseRecord) -> CaseRecord:
        return self.upsert(case)

    def list(self) -> list[CaseRecord]:
        if not psycopg or not self.dsn:
            raise RuntimeError("PostgreSQL indisponível")
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM cases ORDER BY updated_at DESC")
                return [self._case_from_row(conn, row) for row in cur.fetchall()]

    def get(self, case_id: str) -> CaseRecord | None:
        if not psycopg or not self.dsn:
            raise RuntimeError("PostgreSQL indisponível")
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
                row = cur.fetchone()
                return self._case_from_row(conn, row) if row else None

    def upsert(self, case: CaseRecord) -> CaseRecord:
        if not psycopg or not self.dsn:
            raise RuntimeError("PostgreSQL indisponível")
        data = case.model_dump()
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO cases (
                          id, client_name, orgao_name, object, modality, status, current_phase, strategic_score,
                          risks, opportunities, related_memories, context, edital_text, memory_suggestion,
                          raw_payload, created_at, updated_at
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s::jsonb,%s::jsonb,%s,%s)
                        ON CONFLICT (id) DO UPDATE SET
                          client_name = EXCLUDED.client_name,
                          orgao_name = EXCLUDED.orgao_name,
                          object = EXCLUDED.object,
                          modality = EXCLUDED.modality,
                          status = EXCLUDED.status,
                          current_phase = EXCLUDED.current_phase,
                          strategic_score = EXCLUDED.strategic_score,
                          risks = EXCLUDED.risks,
                          opportunities = EXCLUDED.opportunities,
                          related_memories = EXCLUDED.related_memories,
                          context = EXCLUDED.context,
                          edital_text = EXCLUDED.edital_text,
                          memory_suggestion = EXCLUDED.memory_suggestion,
                          raw_payload = EXCLUDED.raw_payload,
                          updated_at = EXCLUDED.updated_at
                        """,
                        (
                            case.id,
                            case.cliente,
                            case.orgao,
                            case.objeto,
                            case.modalidade,
                            case.status,
                            case.fase_atual,
                            case.score_estrategico,
                            json.dumps(case.riscos, ensure_ascii=False),
                            json.dumps(case.oportunidades, ensure_ascii=False),
                            json.dumps(case.memorias_relacionadas, ensure_ascii=False),
                            case.contexto,
                            case.texto_edital,
                            json.dumps(case.memoria_sugerida.model_dump() if case.memoria_sugerida else None, ensure_ascii=False),
                            json.dumps(data, ensure_ascii=False, default=str),
                            case.criado_em,
                            case.atualizado_em,
                        ),
                    )
                    cur.execute("DELETE FROM case_events WHERE case_id = %s", (case.id,))
                    for event in case.historico_operacional:
                        cur.execute(
                            """
                            INSERT INTO case_events (
                              id, case_id, event_type, phase, description, impact, operational_learning,
                              memory_suggestion, raw_payload, created_at
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)
                            ON CONFLICT (id) DO UPDATE SET
                              event_type = EXCLUDED.event_type,
                              phase = EXCLUDED.phase,
                              description = EXCLUDED.description,
                              impact = EXCLUDED.impact,
                              operational_learning = EXCLUDED.operational_learning,
                              memory_suggestion = EXCLUDED.memory_suggestion,
                              raw_payload = EXCLUDED.raw_payload,
                              created_at = EXCLUDED.created_at
                            """,
                            (
                                event.id,
                                case.id,
                                event.tipo,
                                event.fase,
                                event.descricao,
                                event.impacto,
                                event.aprendizado_operacional,
                                json.dumps(event.memoria_sugerida.model_dump() if event.memoria_sugerida else None, ensure_ascii=False),
                                json.dumps(event.model_dump(), ensure_ascii=False, default=str),
                                event.data,
                            ),
                        )
        return case

    def _case_from_row(self, conn: Any, row: dict[str, Any]) -> CaseRecord:
        raw = row.get("raw_payload") or {}
        if isinstance(raw, str):
            raw = json.loads(raw)
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT raw_payload FROM case_events WHERE case_id = %s ORDER BY created_at ASC", (row["id"],))
            events = []
            for event_row in cur.fetchall():
                event_raw = event_row.get("raw_payload") or {}
                if isinstance(event_raw, str):
                    event_raw = json.loads(event_raw)
                events.append(CaseEvent(**event_raw))
        raw["historico_operacional"] = [event.model_dump() for event in events]
        return CaseRecord(**raw)

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith("LICI_DATABASE_URL="):
                    return line.split("=", 1)[1].strip()
        except FileNotFoundError:
            return None
        return None
