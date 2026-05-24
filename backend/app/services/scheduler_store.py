from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from app.schemas.scheduler import SchedulerConfig, SchedulerRunLog


class JsonSchedulerStore:
    def __init__(
        self,
        root: Path | str = "/root/lici-app/scheduler",
        config_path: Path | str | None = None,
        logs_path: Path | str | None = None,
    ):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.config_path = Path(config_path) if config_path else self.root / "config.json"
        self.logs_path = Path(logs_path) if logs_path else self.root / "logs.json"
        if not self.config_path.exists():
            self.write_config(SchedulerConfig())
        if not self.logs_path.exists():
            self._write_json(self.logs_path, [])

    def read_config(self) -> SchedulerConfig:
        return SchedulerConfig(**self._read_json(self.config_path, {}))

    def write_config(self, config: SchedulerConfig) -> SchedulerConfig:
        self._write_json(self.config_path, config.model_dump())
        return config

    def list_logs(self) -> list[SchedulerRunLog]:
        raw = self._read_json(self.logs_path, [])
        return [SchedulerRunLog(**item) for item in raw]

    def append_log(self, log: SchedulerRunLog) -> SchedulerRunLog:
        logs = self.list_logs()
        logs.append(log)
        data = [item.model_dump() for item in logs]
        self._write_json(self.logs_path, data)
        return log

    def _read_json(self, path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)
