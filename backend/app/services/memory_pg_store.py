from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.schemas.memory import MemoryCreate, MemoryRecord

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

POSTGRES_ENV_FILE = Path("/root/lici-app/secrets/postgres.env")


class PostgresMemoryStore:
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

    def create(self, payload: MemoryCreate) -> MemoryRecord:
        record = MemoryRecord(**payload.model_dump())
        self.upsert(record)
        return record

    def upsert(self, record: MemoryRecord) -> MemoryRecord:
        if not psycopg or not self.dsn:
            raise RuntimeError("PostgreSQL indisponível")
        raw = record.model_dump()
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO memories (
                      id, tipo, titulo, descricao, contexto, estrategia, resultado, aprendizado,
                      uso_futuro, tags, fonte, confianca, raw_payload, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      tipo = EXCLUDED.tipo,
                      titulo = EXCLUDED.titulo,
                      descricao = EXCLUDED.descricao,
                      contexto = EXCLUDED.contexto,
                      estrategia = EXCLUDED.estrategia,
                      resultado = EXCLUDED.resultado,
                      aprendizado = EXCLUDED.aprendizado,
                      uso_futuro = EXCLUDED.uso_futuro,
                      tags = EXCLUDED.tags,
                      fonte = EXCLUDED.fonte,
                      confianca = EXCLUDED.confianca,
                      raw_payload = EXCLUDED.raw_payload,
                      updated_at = EXCLUDED.updated_at
                    """,
                    (
                        record.id,
                        record.tipo,
                        record.titulo,
                        record.descricao,
                        record.contexto,
                        record.estrategia,
                        record.resultado,
                        record.aprendizado,
                        record.uso_futuro,
                        record.tags,
                        record.fonte,
                        record.confianca,
                        json.dumps(raw, ensure_ascii=False, default=str),
                        record.data,
                        record.data,
                    ),
                )
        return record

    def list(self, tipo: str | None = None) -> list[MemoryRecord]:
        if not psycopg or not self.dsn:
            raise RuntimeError("PostgreSQL indisponível")
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                if tipo:
                    cur.execute("SELECT raw_payload FROM memories WHERE tipo = %s ORDER BY created_at DESC", (tipo,))
                else:
                    cur.execute("SELECT raw_payload FROM memories ORDER BY created_at DESC")
                return [self._from_raw(row["raw_payload"]) for row in cur.fetchall()]

    def search(self, termo: str, tipo: str | None = None) -> list[MemoryRecord]:
        termo_norm = termo.casefold().strip()
        if not termo_norm:
            return self.list(tipo=tipo)
        items = self.list(tipo=tipo)
        return [item for item in items if termo_norm in self._haystack(item)]

    def _haystack(self, item: MemoryRecord) -> str:
        values = [
            item.tipo,
            item.titulo,
            item.descricao,
            item.contexto,
            item.estrategia,
            item.resultado,
            item.aprendizado,
            item.uso_futuro,
            item.fonte,
            " ".join(item.tags),
        ]
        return "\n".join(values).casefold()

    def _from_raw(self, raw: Any) -> MemoryRecord:
        if isinstance(raw, str):
            raw = json.loads(raw)
        return MemoryRecord(**raw)

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith("LICI_DATABASE_URL="):
                    return line.split("=", 1)[1].strip()
        except FileNotFoundError:
            return None
        return None
