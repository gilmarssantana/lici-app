#!/root/lici-app/backend/.venv/bin/python
from __future__ import annotations

import argparse
import json
import os
import secrets
import string
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/root/lici-app/backend")

from app.services.audit_log import audit_event
from app.services.auth_engine import LiciAuthEngine

AUTH_ROOT = Path("/root/lici-app/auth")
RECOVERY_FILE = AUTH_ROOT / "admin_recovery_credentials"
BOOTSTRAP_FILE = AUTH_ROOT / "admin_bootstrap_credentials"


def generate_password(length: int = 28) -> str:
    alphabet = string.ascii_letters + string.digits + "-_@#%+"
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in value)
            and any(char.isupper() for char in value)
            and any(char.isdigit() for char in value)
        ):
            return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset seguro de senha admin da LICI.")
    parser.add_argument("--usuario", default="liciadmin", help="Usuário admin a redefinir.")
    parser.add_argument("--remove-bootstrap", action="store_true", help="Remove credencial bootstrap antiga após reset.")
    args = parser.parse_args()

    engine = LiciAuthEngine()
    username = args.usuario.strip().lower()
    user = engine._find_by_username(username)
    if not user:
        print(f"ERRO: usuário não encontrado: {username}", file=sys.stderr)
        return 1
    if user.get("perfil") != "admin":
        print(f"ERRO: usuário não é admin: {username}", file=sys.stderr)
        return 1

    password = generate_password()
    now = datetime.now(timezone.utc).isoformat()
    user["senha_hash"] = engine._hash_password(password)
    user["status"] = "ativo"
    user["atualizado_em"] = now
    engine._upsert_user(user)

    AUTH_ROOT.mkdir(parents=True, exist_ok=True)
    os.chmod(AUTH_ROOT, 0o700)
    payload = {
        "created_at": now,
        "usuario": username,
        "senha": password,
        "aviso": "Credencial de recuperação. Use para login e troque/remova depois.",
    }
    RECOVERY_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(RECOVERY_FILE, 0o600)

    removed_bootstrap = False
    if args.remove_bootstrap and BOOTSTRAP_FILE.exists():
        BOOTSTRAP_FILE.unlink()
        removed_bootstrap = True

    audit_event(
        "auth",
        "reset_admin_password",
        "ok",
        {"usuario": username, "recovery_file": str(RECOVERY_FILE), "bootstrap_removido": removed_bootstrap},
        user.get("id"),
    )
    print(f"Senha redefinida para {username}. Credencial salva em {RECOVERY_FILE}.")
    if removed_bootstrap:
        print("Credencial bootstrap antiga removida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
