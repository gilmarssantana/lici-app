from __future__ import annotations

from app.services.audit_log import audit_event
from app.services.auth_pg_store import PostgresAuthStore
from app.services.auth_store import JsonAuthStore


def migrate_auth_json_to_postgres() -> dict[str, int | str]:
    json_store = JsonAuthStore()
    pg_store = PostgresAuthStore()
    if not pg_store.available():
        audit_event("postgres_migration", "auth_json_to_postgres", "erro", {"motivo": "postgres_indisponivel"}, "fase1-auth")
        return {"status": "erro", "migrados": 0}
    migrated = 0
    for user in json_store.list_users():
        pg_store.upsert_user(user)
        migrated += 1
    audit_event("postgres_migration", "auth_json_to_postgres", "ok", {"migrados": migrated}, "fase1-auth")
    return {"status": "ok", "migrados": migrated}


if __name__ == "__main__":
    print(migrate_auth_json_to_postgres())
