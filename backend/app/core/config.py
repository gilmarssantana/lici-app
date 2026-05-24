from __future__ import annotations

import os
from pathlib import Path


class Settings:
    app_name: str = "LICI App"
    memory_root: Path = Path(os.getenv("LICI_MEMORY_ROOT", "/root/lici-app/memoria_viva"))
    memory_core_url: str = os.getenv("LICI_MEMORY_CORE_URL", "http://127.0.0.1:8010")


settings = Settings()
