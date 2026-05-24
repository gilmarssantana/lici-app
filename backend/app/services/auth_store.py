from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

AUTH_ROOT = Path("/root/lici-app/auth")
USERS_FILE = AUTH_ROOT / "usuarios.json"
CONFIG_FILE = AUTH_ROOT / "config.json"

DEFAULT_TOKEN_EXPIRE_MINUTES = 60 * 8


class JsonAuthStore:
    def __init__(self, root: Path | str = AUTH_ROOT):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.users_path = self.root / "usuarios.json"
        self.config_path = self.root / "config.json"
        if not self.users_path.exists():
            self._write_json(self.users_path, [])
        if not self.config_path.exists():
            self._write_json(
                self.config_path,
                {
                    "jwt_secret": secrets.token_urlsafe(48),
                    "jwt_algorithm": "HS256",
                    "access_token_expire_minutes": DEFAULT_TOKEN_EXPIRE_MINUTES,
                    "criado_em": _now_iso(),
                },
            )
        self._chmod_private(self.users_path)
        self._chmod_private(self.config_path)

    def list_users(self) -> list[dict[str, Any]]:
        return json.loads(self.users_path.read_text(encoding="utf-8"))

    def save_users(self, users: list[dict[str, Any]]) -> None:
        self._write_json(self.users_path, users)

    def config(self) -> dict[str, Any]:
        return json.loads(self.config_path.read_text(encoding="utf-8"))

    def find_by_username(self, username: str) -> dict[str, Any] | None:
        normalized = username.strip().lower()
        for user in self.list_users():
            if user.get("usuario", "").strip().lower() == normalized:
                return user
        return None

    def find_by_id(self, user_id: str) -> dict[str, Any] | None:
        for user in self.list_users():
            if user.get("id") == user_id:
                return user
        return None

    def upsert_user(self, user: dict[str, Any]) -> dict[str, Any]:
        users = self.list_users()
        for idx, current in enumerate(users):
            if current.get("id") == user.get("id"):
                users[idx] = user
                self.save_users(users)
                return user
        users.append(user)
        self.save_users(users)
        return user

    def is_empty(self) -> bool:
        return len(self.list_users()) == 0

    def _write_json(self, path: Path, data: dict[str, Any] | list[dict[str, Any]]) -> None:
        with NamedTemporaryFile("w", encoding="utf-8", dir=self.root, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2, default=str)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        os.chmod(tmp_path, 0o600)
        tmp_path.replace(path)
        self._chmod_private(path)

    def _chmod_private(self, path: Path) -> None:
        try:
            os.chmod(path, 0o600)
        except FileNotFoundError:
            pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
