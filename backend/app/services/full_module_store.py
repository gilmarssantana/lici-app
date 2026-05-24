from __future__ import annotations

import json
import os
import time
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, TypeVar

from pydantic import BaseModel

from app.services.audit_log import audit_event

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

POSTGRES_ENV_FILE = Path('/root/lici-app/secrets/postgres.env')
T = TypeVar('T', bound=BaseModel)


class HybridFullModuleStore:
    def __init__(self, module: str, model: type[T], root: str, table: str):
        self.module = module
        self.model = model
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'records.json'
        if not self.path.exists():
            self._write_json([])
        self.table = table
        self.dsn = os.getenv('LICI_DATABASE_URL') or self._dsn_from_env_file()
        self._available_cache = {'checked_at': 0.0, 'available': False}
        self._table_ready = False

    def available(self) -> bool:
        if not psycopg or not self.dsn:
            return False
        now = time.time()
        if now - self._available_cache['checked_at'] <= 15:
            return bool(self._available_cache['available'])
        try:
            with psycopg.connect(self.dsn, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
                    cur.fetchone()
            self._available_cache = {'checked_at': now, 'available': True}
            return True
        except Exception:
            self._available_cache = {'checked_at': now, 'available': False}
            return False

    def list(self, organization_id: str | None = None, tipo: str | None = None, limit: int = 200, offset: int = 0) -> list[T]:
        limit = max(1, min(int(limit or 200), 1000))
        offset = max(0, int(offset or 0))
        try:
            if self.available():
                self._ensure_table()
                with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
                    with conn.cursor() as cur:
                        where = []
                        params: list[Any] = []
                        if organization_id:
                            where.append('organization_id = %s')
                            params.append(organization_id)
                        if tipo:
                            where.append('tipo = %s')
                            params.append(tipo)
                        sql = f"SELECT raw_payload FROM {self.table}"
                        if where:
                            sql += ' WHERE ' + ' AND '.join(where)
                        sql += ' ORDER BY updated_at DESC LIMIT %s OFFSET %s'
                        params.extend([limit, offset])
                        cur.execute(sql, params)
                        return [self.model(**self._raw(row['raw_payload'])) for row in cur.fetchall()]
            audit_event(self.module, 'postgres_fallback_json', 'erro', {'operacao': 'list', 'motivo': 'postgres_indisponivel'})
        except Exception as exc:
            audit_event(self.module, 'postgres_fallback_json', 'erro', {'operacao': 'list', 'erro': str(exc)})
        return self._filter(self._read_json(), organization_id, tipo)[offset:offset + limit]

    def get(self, record_id: str, organization_id: str | None = None) -> T | None:
        items = self.list(organization_id=organization_id, limit=1000)
        for item in items:
            if item.id == record_id:
                return item
        return None

    def exists(self, record_id: str) -> bool:
        try:
            if self.available():
                self._ensure_table()
                with psycopg.connect(self.dsn, connect_timeout=3) as conn:
                    with conn.cursor() as cur:
                        cur.execute(f'SELECT 1 FROM {self.table} WHERE id = %s LIMIT 1', (record_id,))
                        return cur.fetchone() is not None
        except Exception as exc:
            audit_event(self.module, 'postgres_fallback_json', 'erro', {'operacao': 'exists', 'erro': str(exc)}, record_id)
        return any(item.id == record_id for item in self._read_json())

    def upsert(self, item: T) -> T:
        items = self._read_json()
        for idx, current in enumerate(items):
            if current.id == item.id:
                items[idx] = item
                break
        else:
            items.append(item)
        self._write_json([entry.model_dump() for entry in items])
        try:
            if self.available():
                self._ensure_table()
                data = item.model_dump()
                with psycopg.connect(self.dsn, connect_timeout=3) as conn:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            cur.execute(
                                f'''
                                INSERT INTO {self.table} (id, organization_id, tipo, raw_payload, created_at, updated_at)
                                VALUES (%s,%s,%s,%s::jsonb,%s,%s)
                                ON CONFLICT (id) DO UPDATE SET
                                  organization_id = EXCLUDED.organization_id,
                                  tipo = EXCLUDED.tipo,
                                  raw_payload = EXCLUDED.raw_payload,
                                  updated_at = EXCLUDED.updated_at
                                ''',
                                (item.id, getattr(item, 'organization_id', 'default-org') or 'default-org', getattr(item, 'tipo', ''), json.dumps(data, ensure_ascii=False, default=str), getattr(item, 'criado_em', None), getattr(item, 'atualizado_em', None)),
                            )
                audit_event(self.module, 'dual_write_postgres', 'ok', {'operacao': 'upsert'}, item.id)
            else:
                audit_event(self.module, 'dual_write_postgres', 'erro', {'operacao': 'upsert', 'motivo': 'postgres_indisponivel'}, item.id)
        except Exception as exc:
            audit_event(self.module, 'dual_write_postgres', 'erro', {'operacao': 'upsert', 'erro': str(exc)}, item.id)
        return item

    def _filter(self, items: list[T], organization_id: str | None, tipo: str | None) -> list[T]:
        if organization_id:
            items = [item for item in items if (getattr(item, 'organization_id', None) or 'default-org') == organization_id]
        if tipo:
            items = [item for item in items if getattr(item, 'tipo', None) == tipo]
        return sorted(items, key=lambda item: getattr(item, 'atualizado_em', None) or getattr(item, 'criado_em', None), reverse=True)

    def _read_json(self) -> list[T]:
        raw = json.loads(self.path.read_text(encoding='utf-8'))
        return [self.model(**item) for item in raw]

    def _write_json(self, data: list[dict[str, Any]]) -> None:
        with NamedTemporaryFile('w', encoding='utf-8', dir=self.root, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2, default=str)
            tmp.write('\n')
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.path)

    def _ensure_table(self) -> None:
        if self._table_ready:
            return
        if not psycopg or not self.dsn:
            raise RuntimeError('PostgreSQL indisponível')
        with psycopg.connect(self.dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.table} (
                        id TEXT PRIMARY KEY,
                        organization_id TEXT NOT NULL DEFAULT 'default-org',
                        tipo TEXT NOT NULL,
                        raw_payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ,
                        updated_at TIMESTAMPTZ
                    )
                ''')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_org ON {self.table} (organization_id)')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_tipo ON {self.table} (tipo)')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_org_tipo_updated ON {self.table} (organization_id, tipo, updated_at DESC)')
            conn.commit()
        self._table_ready = True

    def _raw(self, raw: Any) -> dict[str, Any]:
        return json.loads(raw) if isinstance(raw, str) else dict(raw or {})

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding='utf-8').splitlines():
                if line.startswith('LICI_DATABASE_URL='):
                    return line.split('=', 1)[1].strip()
        except FileNotFoundError:
            return None
        return None
