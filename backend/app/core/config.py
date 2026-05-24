from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_ROOT = Path(os.getenv("LICI_APP_ROOT", "/root/lici-app"))
DEFAULT_ENV_FILES = (
    APP_ROOT / "config" / "lici.env",
    APP_ROOT / "secrets" / "postgres.env",
)


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


for env_file in DEFAULT_ENV_FILES:
    _load_env_file(env_file)


def _path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default)).expanduser()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _str(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    app_name: str = _str("LICI_APP_NAME", "LICI App")
    environment: str = _str("LICI_ENV", "production")
    app_root: Path = _path("LICI_APP_ROOT", "/root/lici-app")
    docs_root: Path = _path("LICI_DOCS_ROOT", "/root/lici-docs")
    backup_root: Path = _path("LICI_BACKUP_ROOT", "/root/backups/lici")

    api_host: str = _str("LICI_API_HOST", "127.0.0.1")
    api_port: int = _int("LICI_API_PORT", 8100)
    memory_host: str = _str("LICI_MEMORY_HOST", "127.0.0.1")
    memory_port: int = _int("LICI_MEMORY_PORT", 8010)
    frontend_host: str = _str("LICI_FRONTEND_HOST", "127.0.0.1")
    frontend_port: int = _int("LICI_FRONTEND_PORT", 5173)
    rag_host: str = _str("LICI_RAG_HOST", "127.0.0.1")
    rag_port: int = _int("LICI_RAG_PORT", 8000)

    public_url: str = _str("LICI_PUBLIC_URL", "https://licitaprobrasil.com/")
    public_domain: str = _str("LICI_PUBLIC_DOMAIN", "licitaprobrasil.com")

    memory_root: Path = _path("LICI_MEMORY_ROOT", "/root/lici-app/memoria_viva")
    auth_root: Path = _path("LICI_AUTH_ROOT", "/root/lici-app/auth")
    secrets_root: Path = _path("LICI_SECRETS_ROOT", "/root/lici-app/secrets")
    logs_root: Path = _path("LICI_LOGS_ROOT", "/root/lici-app/logs")
    audit_log: Path = _path("LICI_AUDIT_LOG", "/root/lici-app/audit/audit.log")

    backup_max_age_hours: int = _int("LICI_BACKUP_MAX_AGE_HOURS", 36)
    backup_keep_count: int = _int("LICI_BACKUP_KEEP_COUNT", 7)

    @property
    def api_url(self) -> str:
        return f"http://{self.api_host}:{self.api_port}"

    @property
    def memory_core_url(self) -> str:
        return _str("LICI_MEMORY_CORE_URL", f"http://{self.memory_host}:{self.memory_port}")

    @property
    def frontend_url(self) -> str:
        return f"http://{self.frontend_host}:{self.frontend_port}"

    @property
    def rag_url(self) -> str:
        return _str("LICI_RAG_URL", f"http://{self.rag_host}:{self.rag_port}")

    @property
    def postgres_env_file(self) -> Path:
        return self.secrets_root / "postgres.env"

    def public_snapshot(self) -> dict[str, object]:
        return {
            "app_name": self.app_name,
            "environment": self.environment,
            "app_root": str(self.app_root),
            "docs_root": str(self.docs_root),
            "backup_root": str(self.backup_root),
            "api_url": self.api_url,
            "memory_core_url": self.memory_core_url,
            "frontend_url": self.frontend_url,
            "rag_url": self.rag_url,
            "public_url": self.public_url,
            "backup_max_age_hours": self.backup_max_age_hours,
            "backup_keep_count": self.backup_keep_count,
        }


settings = Settings()
