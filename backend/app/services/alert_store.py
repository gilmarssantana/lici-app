from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from app.schemas.alert import AlertGenerateLog, AlertRecord
from app.services.audit_log import audit_event
from app.services.radar_pg_store import PostgresAlertStore


class JsonAlertStore:
    def __init__(self, root: Path | str = "/root/lici-app/alertas"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.alerts_path = self.root / "alertas.json"
        self.logs_path = self.root / "logs.json"
        if not self.alerts_path.exists():
            self._write_json(self.alerts_path, [])
        if not self.logs_path.exists():
            self._write_json(self.logs_path, [])

    def list_alerts(self) -> list[AlertRecord]:
        raw = self._read_json(self.alerts_path, [])
        return [AlertRecord(**item) for item in raw]

    def write_alerts(self, alerts: list[AlertRecord]) -> list[AlertRecord]:
        self._write_json(self.alerts_path, [item.model_dump() for item in alerts])
        return alerts

    def upsert_many(self, incoming: list[AlertRecord]) -> tuple[list[AlertRecord], int, int]:
        existing = self.list_alerts()
        by_key = {item.chave: item for item in existing}
        novos = 0
        atualizados = 0
        saved: list[AlertRecord] = []
        for alert in incoming:
            current = by_key.get(alert.chave)
            if current:
                alert.id = current.id
                alert.criado_em = current.criado_em
                alert.lido = current.lido
                atualizados += 1
            else:
                novos += 1
            by_key[alert.chave] = alert
            saved.append(alert)
        self.write_alerts(list(by_key.values()))
        return saved, novos, atualizados

    def get(self, alert_id: str) -> AlertRecord | None:
        for item in self.list_alerts():
            if item.id == alert_id:
                return item
        return None

    def update(self, updated: AlertRecord) -> AlertRecord:
        alerts = self.list_alerts()
        for idx, item in enumerate(alerts):
            if item.id == updated.id:
                alerts[idx] = updated
                self.write_alerts(alerts)
                return updated
        alerts.append(updated)
        self.write_alerts(alerts)
        return updated

    def list_logs(self) -> list[AlertGenerateLog]:
        raw = self._read_json(self.logs_path, [])
        return [AlertGenerateLog(**item) for item in raw]

    def append_log(self, log: AlertGenerateLog) -> AlertGenerateLog:
        logs = self.list_logs()
        logs.append(log)
        self._write_json(self.logs_path, [item.model_dump() for item in logs])
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


class HybridAlertStore:
    """Alertas dual-read/dual-write: read PostgreSQL first with JSON fallback; write JSON mandatory + PostgreSQL best-effort."""

    def __init__(self, json_store: JsonAlertStore | None = None, pg_store: PostgresAlertStore | None = None):
        self.json_store = json_store or JsonAlertStore()
        self.pg_store = pg_store or PostgresAlertStore()

    def list_alerts(self) -> list[AlertRecord]:
        try:
            if self.pg_store.available():
                return self.pg_store.list_alerts()
            audit_event("alert_engine", "postgres_fallback_json", "erro", {"operacao": "list_alerts", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("alert_engine", "postgres_fallback_json", "erro", {"operacao": "list_alerts", "erro": str(exc)})
        return self.json_store.list_alerts()

    def write_alerts(self, alerts: list[AlertRecord]) -> list[AlertRecord]:
        saved = self.json_store.write_alerts(alerts)
        self._try_pg_alerts(saved, "write_alerts")
        return saved

    def upsert_many(self, incoming: list[AlertRecord]) -> tuple[list[AlertRecord], int, int]:
        saved, novos, atualizados = self.json_store.upsert_many(incoming)
        self._try_pg_alerts(saved, "upsert_many")
        return saved, novos, atualizados

    def get(self, alert_id: str) -> AlertRecord | None:
        try:
            if self.pg_store.available():
                return self.pg_store.get(alert_id)
            audit_event("alert_engine", "postgres_fallback_json", "erro", {"operacao": "get", "motivo": "postgres_indisponivel", "alert_id": alert_id}, alert_id)
        except Exception as exc:
            audit_event("alert_engine", "postgres_fallback_json", "erro", {"operacao": "get", "alert_id": alert_id, "erro": str(exc)}, alert_id)
        return self.json_store.get(alert_id)

    def update(self, updated: AlertRecord) -> AlertRecord:
        saved = self.json_store.update(updated)
        self._try_pg_alert(saved, "update")
        return saved

    def list_logs(self) -> list[AlertGenerateLog]:
        try:
            if self.pg_store.available():
                return self.pg_store.list_logs()
            audit_event("alert_engine", "postgres_fallback_json", "erro", {"operacao": "list_logs", "motivo": "postgres_indisponivel"})
        except Exception as exc:
            audit_event("alert_engine", "postgres_fallback_json", "erro", {"operacao": "list_logs", "erro": str(exc)})
        return self.json_store.list_logs()

    def append_log(self, log: AlertGenerateLog) -> AlertGenerateLog:
        saved = self.json_store.append_log(log)
        try:
            if self.pg_store.available():
                self.pg_store.append_log(saved)
                audit_event("alert_engine", "dual_write_postgres", "ok", {"operacao": "append_log"}, saved.id)
            else:
                audit_event("alert_engine", "dual_write_postgres", "erro", {"operacao": "append_log", "motivo": "postgres_indisponivel"}, saved.id)
        except Exception as exc:
            audit_event("alert_engine", "dual_write_postgres", "erro", {"operacao": "append_log", "erro": str(exc)}, saved.id)
        return saved

    def _try_pg_alerts(self, alerts: list[AlertRecord], operation: str) -> None:
        try:
            if self.pg_store.available():
                self.pg_store.write_alerts(alerts)
                audit_event("alert_engine", "dual_write_postgres", "ok", {"operacao": operation, "total": len(alerts)})
            else:
                audit_event("alert_engine", "dual_write_postgres", "erro", {"operacao": operation, "motivo": "postgres_indisponivel", "total": len(alerts)})
        except Exception as exc:
            audit_event("alert_engine", "dual_write_postgres", "erro", {"operacao": operation, "erro": str(exc), "total": len(alerts)})

    def _try_pg_alert(self, alert: AlertRecord, operation: str) -> None:
        try:
            if self.pg_store.available():
                self.pg_store.upsert_alert(alert)
                audit_event("alert_engine", "dual_write_postgres", "ok", {"operacao": operation}, alert.id)
            else:
                audit_event("alert_engine", "dual_write_postgres", "erro", {"operacao": operation, "motivo": "postgres_indisponivel"}, alert.id)
        except Exception as exc:
            audit_event("alert_engine", "dual_write_postgres", "erro", {"operacao": operation, "erro": str(exc)}, alert.id)
