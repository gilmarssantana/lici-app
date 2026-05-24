from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover - fallback when dependency/db unavailable
    psycopg = None
    dict_row = None

POSTGRES_ENV_FILE = Path("/root/lici-app/secrets/postgres.env")


class PostgresAuthStore:
    """PostgreSQL Auth store with safe fallback semantics.

    Any caller should treat unavailable DB as non-fatal and continue with JSON.
    """

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

    def list_users(self) -> list[dict[str, Any]]:
        if not psycopg or not self.dsn:
            raise RuntimeError("PostgreSQL indisponível")
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.*, COALESCE(array_agg(DISTINCT p.code) FILTER (WHERE p.code IS NOT NULL), '{}') AS permissoes
                    FROM users u
                    LEFT JOIN user_roles ur ON ur.user_id = u.id
                    LEFT JOIN roles r ON r.id = ur.role_id
                    LEFT JOIN role_permissions rp ON rp.role_id = r.id
                    LEFT JOIN permissions p ON p.id = rp.permission_id
                    GROUP BY u.id
                    ORDER BY u.created_at ASC
                    """
                )
                return [self._from_row(row) for row in cur.fetchall()]

    def find_by_username(self, username: str) -> dict[str, Any] | None:
        users = self.list_users()
        normalized = username.strip().lower()
        return next((user for user in users if user.get("usuario") == normalized), None)

    def find_by_id(self, user_id: str) -> dict[str, Any] | None:
        users = self.list_users()
        return next((user for user in users if user.get("id") == user_id), None)

    def upsert_user(self, user: dict[str, Any]) -> dict[str, Any]:
        if not psycopg or not self.dsn:
            raise RuntimeError("PostgreSQL indisponível")
        permissions = list(dict.fromkeys(user.get("permissoes") or []))
        role_code = user.get("perfil") or "fornecedor"
        with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO users (id, username, name, password_hash, profile, operational_profile, status, last_login_at, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                          username = EXCLUDED.username,
                          name = EXCLUDED.name,
                          password_hash = EXCLUDED.password_hash,
                          profile = EXCLUDED.profile,
                          operational_profile = EXCLUDED.operational_profile,
                          status = EXCLUDED.status,
                          last_login_at = EXCLUDED.last_login_at,
                          updated_at = EXCLUDED.updated_at
                        """,
                        (
                            user["id"],
                            user["usuario"],
                            user["nome"],
                            user["senha_hash"],
                            user["perfil"],
                            user["perfil_operacional"],
                            user.get("status", "ativo"),
                            user.get("ultimo_login_em"),
                            user.get("criado_em") or datetime.utcnow().isoformat(),
                            user.get("atualizado_em") or datetime.utcnow().isoformat(),
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO roles (code, name, description)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, updated_at = now()
                        RETURNING id
                        """,
                        (role_code, role_code, f"Perfil {role_code} da LICI"),
                    )
                    role_id = cur.fetchone()["id"]
                    cur.execute("DELETE FROM user_roles WHERE user_id = %s", (user["id"],))
                    cur.execute("INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user["id"], role_id))
                    for permission in permissions:
                        cur.execute(
                            """
                            INSERT INTO permissions (code, description)
                            VALUES (%s, %s)
                            ON CONFLICT (code) DO UPDATE SET description = COALESCE(permissions.description, EXCLUDED.description)
                            RETURNING id
                            """,
                            (permission, f"Permissão {permission}"),
                        )
                        permission_id = cur.fetchone()["id"]
                        cur.execute(
                            "INSERT INTO role_permissions (role_id, permission_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (role_id, permission_id),
                        )
        return user

    def _from_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "usuario": row["username"],
            "nome": row["name"],
            "senha_hash": row["password_hash"],
            "perfil": row["profile"],
            "perfil_operacional": row["operational_profile"],
            "permissoes": list(row.get("permissoes") or []),
            "status": row["status"],
            "criado_em": _iso(row.get("created_at")),
            "atualizado_em": _iso(row.get("updated_at")),
            "ultimo_login_em": _iso(row.get("last_login_at")) if row.get("last_login_at") else None,
        }

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith("LICI_DATABASE_URL="):
                    return line.split("=", 1)[1].strip()
        except FileNotFoundError:
            return None
        return None


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
