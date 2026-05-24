from __future__ import annotations

import gzip
import json
import os
import shutil
import subprocess
import time
import resource
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
from urllib.error import URLError
from urllib.request import urlopen

from app.services.audit_log import audit_event

LOG_DIR = Path("/root/lici-app/logs")
MAX_LOG_BYTES = 10 * 1024 * 1024
ROTATE_KEEP = 7

_STATUS_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}

LOG_FILES = {
    "api": LOG_DIR / "api.jsonl",
    "memory_core": LOG_DIR / "memory_core.jsonl",
    "scheduler": LOG_DIR / "scheduler.jsonl",
    "backup": LOG_DIR / "backup.jsonl",
    "healthcheck": LOG_DIR / "healthcheck.jsonl",
    "alerts": LOG_DIR / "alerts.jsonl",
}

CRITICAL_EVENT_TYPES = {
    "backup_failed",
    "postgres_unavailable",
    "timer_stopped",
    "api_slow",
    "healthcheck_error",
    "service_down",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    for path in LOG_FILES.values():
        path.touch(exist_ok=True)


def rotate_log(path: Path, max_bytes: int = MAX_LOG_BYTES, keep: int = ROTATE_KEEP) -> None:
    try:
        if not path.exists() or path.stat().st_size < max_bytes:
            return
        oldest = path.with_name(f"{path.name}.{keep}.gz")
        if oldest.exists():
            oldest.unlink()
        for idx in range(keep - 1, 0, -1):
            src = path.with_name(f"{path.name}.{idx}.gz")
            dst = path.with_name(f"{path.name}.{idx + 1}.gz")
            if src.exists():
                src.rename(dst)
        with path.open("rb") as src, gzip.open(path.with_name(f"{path.name}.1.gz"), "wb") as dst:
            shutil.copyfileobj(src, dst)
        path.write_text("", encoding="utf-8")
    except Exception:
        # Observabilidade nunca deve derrubar operação principal.
        pass


def structured_log(component: str, event: str, status: str = "ok", details: dict[str, Any] | None = None, level: str | None = None) -> dict[str, Any]:
    ensure_log_dir()
    path = LOG_FILES.get(component, LOG_DIR / f"{component}.jsonl")
    rotate_log(path)
    payload = {
        "id": str(uuid4()),
        "timestamp": utc_now(),
        "component": component,
        "event": event,
        "status": status,
        "level": level or _level_from_status(status),
        "details": details or {},
    }
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass

    if status in {"erro", "error", "critical"} or event in CRITICAL_EVENT_TYPES:
        try:
            with LOG_FILES["alerts"].open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass
        if event in CRITICAL_EVENT_TYPES or status in {"erro", "critical"}:
            audit_event("observabilidade", event, "erro" if status != "ok" else "alerta", details or {}, payload["id"])
    return payload


def _level_from_status(status: str) -> str:
    if status in {"erro", "error", "critical"}:
        return "error"
    if status in {"alerta", "warning"}:
        return "warning"
    return "info"


class ObservabilityService:
    def status(self) -> dict[str, Any]:
        ensure_log_dir()
        cached = _STATUS_CACHE.get("data")
        if cached and time.time() - float(_STATUS_CACHE.get("ts", 0)) <= 5:
            data = dict(cached)
            data["cache"] = {"hit": True, "ttl_s": 5}
            return data
        started = time.perf_counter()
        services = self.services_status()
        timers = self.timers_status()
        postgres = self.postgres_status()
        disk = self.disk_status()
        backups = self.backup_status()
        healthchecks = self.healthcheck_status()
        notificacoes = self.notification_status()
        api_metrics = self.api_metrics()
        recent_errors = self.recent_errors(limit=30)
        runtime = self.runtime_status()
        log_growth = self.log_growth_status()
        alerts = self.technical_alerts(services, timers, postgres, disk, backups, healthchecks, api_metrics)
        status = "erro" if any(a["severidade"] == "erro" for a in alerts) else ("alerta" if alerts else "ok")
        response = {
            "status": status,
            "timestamp": utc_now(),
            "tempo_resposta_ms": round((time.perf_counter() - started) * 1000, 2),
            "metricas": {
                "api": api_metrics,
                "postgresql": postgres,
                "disco": disk,
                "servicos": services,
                "timers": timers,
                "backups": backups,
                "healthchecks": healthchecks,
                "notificacoes": notificacoes,
                "runtime": runtime,
                "logs": log_growth,
            },
            "dashboard_tecnico": {
                "erros_recentes": recent_errors,
                "servicos": services,
                "timers": timers,
                "postgresql": postgres,
                "backups": backups,
                "healthchecks": healthchecks,
                "notificacoes": notificacoes,
                "runtime": runtime,
                "logs": log_growth,
            },
            "alertas_tecnicos": alerts,
            "logs": {key: str(path) for key, path in LOG_FILES.items()},
            "cache": {"hit": False, "ttl_s": 5},
        }
        structured_log("api", "observability_status", status, {"alertas": len(alerts), "tempo_resposta_ms": response["tempo_resposta_ms"]})
        _STATUS_CACHE.update({"ts": time.time(), "data": response})
        return response

    def services_status(self) -> list[dict[str, Any]]:
        units = ["lici-api", "lici-memory", "lici-frontend", "nginx", "postgresql", "postgresql@16-main"]
        return [self._systemctl_unit(unit, expected="active") for unit in units]

    def timers_status(self) -> list[dict[str, Any]]:
        timers = ["lici-healthcheck.timer", "lici-scheduler.timer", "lici-backup.timer", "lici-log-rotate.timer"]
        items = []
        for timer in timers:
            item = self._systemctl_unit(timer, expected="active")
            item["proxima_execucao"] = self._timer_next(timer)
            items.append(item)
        return items

    def postgres_status(self) -> dict[str, Any]:
        started = time.perf_counter()
        status = {"status": "ok", "pg_isready": False, "database_size": None, "tables": {}, "query_tempo_ms": None, "indices_v02": {}, "erro": ""}
        try:
            result = subprocess.run(["pg_isready"], capture_output=True, text=True, timeout=5, check=False)
            status["pg_isready"] = result.returncode == 0
            if not status["pg_isready"]:
                status["status"] = "erro"
                status["erro"] = (result.stdout or result.stderr).strip()
        except Exception as exc:
            status.update({"status": "erro", "erro": str(exc)})

        dsn = self._postgres_dsn()
        if dsn:
            try:
                import psycopg

                with psycopg.connect(dsn, connect_timeout=3) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
                        status["database_size"] = cur.fetchone()[0]
                        cur.execute("SELECT pg_database_size(current_database())")
                        status["database_size_bytes"] = cur.fetchone()[0]
                        for table in ["users", "cases", "memories", "radar_opportunities", "triage_items", "alerts", "orgaos", "competitors", "competitor_events", "uploaded_documents", "generated_documents", "exported_files", "chat_sessions", "chat_messages", "chat_metrics", "fornecedor_full_records", "consultor_full_records"]:
                            try:
                                cur.execute(f"SELECT count(*) FROM {table}")
                                status["tables"][table] = cur.fetchone()[0]
                            except Exception as exc:  # tabela ausente não derruba status inteiro
                                status["tables"][table] = f"erro: {exc}"
                        for index in ["idx_fornecedor_full_records_org_tipo_updated", "idx_consultor_full_records_org_tipo_updated"]:
                            cur.execute("SELECT to_regclass(%s)", (index,))
                            status["indices_v02"][index] = bool(cur.fetchone()[0])
                        status["query_tempo_ms"] = round((time.perf_counter() - started) * 1000, 2)
            except Exception as exc:
                status.update({"status": "erro", "erro": str(exc)})
        else:
            status.update({"status": "alerta", "erro": "LICI_DATABASE_URL não encontrado"})
        if status["query_tempo_ms"] is None:
            status["query_tempo_ms"] = round((time.perf_counter() - started) * 1000, 2)
        if status["status"] == "erro":
            structured_log("api", "postgres_unavailable", "erro", status)
        return status

    def runtime_status(self) -> dict[str, Any]:
        try:
            load1, load5, load15 = os.getloadavg()
        except Exception:
            load1 = load5 = load15 = 0.0
        memory = {"rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2)}
        return {"cpu_load": {"1m": round(load1, 2), "5m": round(load5, 2), "15m": round(load15, 2)}, "memoria_processo": memory}

    def log_growth_status(self) -> dict[str, Any]:
        result = {}
        for key, path in LOG_FILES.items():
            try:
                result[key] = {"path": str(path), "size_bytes": path.stat().st_size, "size_mb": round(path.stat().st_size / 1024**2, 3)}
            except FileNotFoundError:
                result[key] = {"path": str(path), "size_bytes": 0, "size_mb": 0}
        return result

    def disk_status(self) -> dict[str, Any]:
        usage = shutil.disk_usage("/")
        used_pct = round((usage.used / usage.total) * 100, 2)
        status = "erro" if used_pct >= 90 else ("alerta" if used_pct >= 80 else "ok")
        return {
            "status": status,
            "mount": "/",
            "total_gb": round(usage.total / 1024**3, 2),
            "usado_gb": round(usage.used / 1024**3, 2),
            "livre_gb": round(usage.free / 1024**3, 2),
            "uso_percentual": used_pct,
        }

    def backup_status(self) -> dict[str, Any]:
        backup_dir = Path("/root/backups/lici")
        backups = sorted(backup_dir.glob("lici-backup-*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True) if backup_dir.exists() else []
        pg_dumps = sorted((backup_dir / "postgres").glob("lici-*.sql.gz"), key=lambda p: p.stat().st_mtime, reverse=True) if (backup_dir / "postgres").exists() else []
        latest = backups[0] if backups else None
        latest_pg = pg_dumps[0] if pg_dumps else None
        now = time.time()
        age_hours = round((now - latest.stat().st_mtime) / 3600, 2) if latest else None
        status = "ok" if latest and age_hours is not None and age_hours <= 36 else "erro"
        result = {
            "status": status,
            "ultimo_backup": str(latest) if latest else None,
            "ultimo_backup_horas": age_hours,
            "ultimo_dump_postgres": str(latest_pg) if latest_pg else None,
            "total_backups": len(backups),
            "total_dumps_postgres": len(pg_dumps),
        }
        if status == "erro":
            structured_log("backup", "backup_failed", "erro", result)
        return result

    def healthcheck_status(self) -> dict[str, Any]:
        legacy = Path("/root/lici-app/health/healthcheck.log")
        structured = LOG_FILES["healthcheck"]
        latest_status = self._latest_status_final(legacy)
        result = {
            "status": "ok" if latest_status == "OK" else "erro",
            "ultimo_status_final": latest_status,
            "log_legado": str(legacy),
            "log_json": str(structured),
            "ultimos_erros": self._grep_tail(legacy, ["ERRO", "ALERTA"], limit=10),
        }
        if result["status"] == "erro":
            structured_log("healthcheck", "healthcheck_error", "erro", result)
        return result

    def notification_status(self) -> dict[str, Any]:
        config = Path("/root/lici-app/notificacoes/config.json")
        logs_path = Path("/root/lici-app/notificacoes/logs.json")
        result = {"status": "desabilitado", "enabled": False, "provider": "telegram", "logs_total": 0, "enviadas_24h": 0, "erros_24h": 0, "bloqueadas_antispam_24h": 0, "ultimo_status": None, "config": str(config), "logs": str(logs_path)}
        try:
            if config.exists():
                cfg = json.loads(config.read_text(encoding="utf-8"))
                result["enabled"] = bool(cfg.get("enabled"))
                result["provider"] = cfg.get("provider", "telegram")
                result["status"] = "ativo" if result["enabled"] else "desabilitado"
            if logs_path.exists():
                logs = json.loads(logs_path.read_text(encoding="utf-8"))
                if not isinstance(logs, list):
                    logs = []
                result["logs_total"] = len(logs)
                recent = [log for log in logs if self._within_hours(log.get("timestamp"), 24)]
                result["enviadas_24h"] = sum(1 for log in recent if log.get("status") == "enviado")
                result["erros_24h"] = sum(1 for log in recent if log.get("status") == "erro")
                result["bloqueadas_antispam_24h"] = sum(1 for log in recent if log.get("status") == "bloqueado_antispam")
                result["ultimo_status"] = logs[-1].get("status") if logs else None
        except Exception as exc:
            result.update({"status": "erro", "erro": str(exc)})
        return result

    def api_metrics(self) -> dict[str, Any]:
        events = self._read_jsonl(LOG_FILES["api"], limit=2000)
        requests = [e for e in events if e.get("event") == "http_request"]
        if not requests:
            return {"total_requisicoes_amostra": 0, "tempo_medio_ms": 0, "tempo_p95_ms": 0, "erros_4xx": 0, "erros_5xx": 0, "lentas": 0, "por_endpoint": [], "endpoints_mais_lentos": [], "taxa_erro_por_endpoint": []}
        durations = sorted(float(e.get("details", {}).get("duration_ms", 0) or 0) for e in requests)
        p95_idx = min(len(durations) - 1, int(len(durations) * 0.95))
        def is_expected_auth_block(event: dict[str, Any]) -> bool:
            return bool((event.get("details", {}) or {}).get("expected_auth_block"))

        erros_4xx = sum(1 for e in requests if not is_expected_auth_block(e) and 400 <= int(e.get("details", {}).get("status_code", 0) or 0) < 500)
        erros_5xx = sum(1 for e in requests if not is_expected_auth_block(e) and int(e.get("details", {}).get("status_code", 0) or 0) >= 500)
        lentas = sum(1 for d in durations if d >= 2000)
        por_organizacao: dict[str, dict[str, Any]] = {}
        por_endpoint: dict[str, dict[str, Any]] = {}
        for event in requests:
            details = event.get("details", {}) or {}
            org = details.get("organization_id") or details.get("active_organization_id") or "default-org"
            bucket = por_organizacao.setdefault(org, {"requisicoes": 0, "falhas": 0, "usuarios": set()})
            bucket["requisicoes"] += 1
            expected_auth_block = is_expected_auth_block(event)
            if not expected_auth_block and (int(details.get("status_code", 0) or 0) >= 400 or event.get("status") in {"erro", "error", "critical"}):
                bucket["falhas"] += 1
            if details.get("user_id") or details.get("username"):
                bucket["usuarios"].add(details.get("user_id") or details.get("username"))
            path = details.get("path") or "desconhecido"
            ep = por_endpoint.setdefault(path, {"requisicoes": 0, "falhas": 0, "duracoes": []})
            ep["requisicoes"] += 1
            ep["duracoes"].append(float(details.get("duration_ms", 0) or 0))
            if not expected_auth_block and int(details.get("status_code", 0) or 0) >= 400:
                ep["falhas"] += 1
        result = {
            "total_requisicoes_amostra": len(requests),
            "tempo_medio_ms": round(sum(durations) / len(durations), 2),
            "tempo_p95_ms": round(durations[p95_idx], 2),
            "erros_4xx": erros_4xx,
            "erros_5xx": erros_5xx,
            "lentas": lentas,
            "por_organizacao": {org: {"requisicoes": data["requisicoes"], "falhas": data["falhas"], "usuarios_ativos": len(data["usuarios"])} for org, data in por_organizacao.items()},
            "por_endpoint": [
                {"endpoint": path, "requisicoes": data["requisicoes"], "falhas": data["falhas"], "tempo_medio_ms": round(sum(data["duracoes"]) / max(len(data["duracoes"]), 1), 2)}
                for path, data in sorted(por_endpoint.items(), key=lambda kv: kv[1]["requisicoes"], reverse=True)[:20]
            ],
            "endpoints_mais_lentos": [
                {"endpoint": path, "tempo_medio_ms": round(sum(data["duracoes"]) / max(len(data["duracoes"]), 1), 2), "requisicoes": data["requisicoes"]}
                for path, data in sorted(por_endpoint.items(), key=lambda kv: sum(kv[1]["duracoes"]) / max(len(kv[1]["duracoes"]), 1), reverse=True)[:10]
            ],
            "taxa_erro_por_endpoint": [
                {"endpoint": path, "taxa_erro_pct": round((data["falhas"] / max(data["requisicoes"], 1)) * 100, 2), "falhas": data["falhas"], "requisicoes": data["requisicoes"]}
                for path, data in sorted(por_endpoint.items(), key=lambda kv: (kv[1]["falhas"] / max(kv[1]["requisicoes"], 1)), reverse=True)[:10] if data["falhas"]
            ],
        }
        if result["tempo_p95_ms"] >= 2000:
            structured_log("api", "api_slow", "alerta", result)
        return result

    def recent_errors(self, limit: int = 30) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        for component, path in LOG_FILES.items():
            for event in self._read_jsonl(path, limit=500):
                if event.get("status") in {"erro", "error", "critical"} or event.get("level") in {"error", "critical"}:
                    item = dict(event)
                    item["log_component"] = component
                    errors.append(item)
        errors.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
        return errors[:limit]

    def technical_alerts(self, services: list[dict[str, Any]], timers: list[dict[str, Any]], postgres: dict[str, Any], disk: dict[str, Any], backups: dict[str, Any], healthchecks: dict[str, Any], api_metrics: dict[str, Any]) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        for service in services:
            if service.get("status") != "ok":
                alerts.append({"tipo": "service_down", "severidade": "erro", "mensagem": f"Serviço {service['unit']} não está ativo", "detalhes": service})
        for timer in timers:
            if timer.get("status") != "ok":
                alerts.append({"tipo": "timer_stopped", "severidade": "erro", "mensagem": f"Timer {timer['unit']} não está ativo", "detalhes": timer})
        if postgres.get("status") != "ok":
            alerts.append({"tipo": "postgres_unavailable", "severidade": "erro", "mensagem": "PostgreSQL indisponível ou degradado", "detalhes": postgres})
        if backups.get("status") != "ok":
            alerts.append({"tipo": "backup_failed", "severidade": "erro", "mensagem": "Backup ausente, antigo ou falho", "detalhes": backups})
        if healthchecks.get("status") != "ok":
            alerts.append({"tipo": "healthcheck_error", "severidade": "erro", "mensagem": "Healthcheck recente indica erro/alerta", "detalhes": healthchecks})
        if api_metrics.get("tempo_p95_ms", 0) >= 2000:
            alerts.append({"tipo": "api_slow", "severidade": "alerta", "mensagem": "API lenta no p95 da amostra", "detalhes": api_metrics})
        if disk.get("status") != "ok":
            alerts.append({"tipo": "disk_usage", "severidade": disk.get("status"), "mensagem": "Uso de disco elevado", "detalhes": disk})
        for alert in alerts:
            if alert["tipo"] in CRITICAL_EVENT_TYPES:
                audit_event("observabilidade", alert["tipo"], "erro" if alert["severidade"] == "erro" else "alerta", alert)
        return alerts

    def _systemctl_unit(self, unit: str, expected: str = "active") -> dict[str, Any]:
        try:
            result = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True, timeout=5, check=False)
            state = (result.stdout or result.stderr).strip()
            status = "ok" if state == expected else "erro"
            if status == "erro":
                structured_log("api", "timer_stopped" if unit.endswith(".timer") else "service_down", "erro", {"unit": unit, "state": state})
            return {"unit": unit, "status": status, "state": state}
        except Exception as exc:
            return {"unit": unit, "status": "erro", "state": "erro", "erro": str(exc)}

    def _timer_next(self, timer: str) -> str | None:
        try:
            result = subprocess.run(["systemctl", "show", timer, "--property=NextElapseUSecRealtime", "--value"], capture_output=True, text=True, timeout=5, check=False)
            value = result.stdout.strip()
            return value or None
        except Exception:
            return None

    def _postgres_dsn(self) -> str | None:
        env = os.getenv("LICI_DATABASE_URL")
        if env:
            return env
        path = Path("/root/lici-app/secrets/postgres.env")
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("LICI_DATABASE_URL="):
                    return line.split("=", 1)[1].strip()
        except FileNotFoundError:
            return None
        return None

    def _within_hours(self, value: str | None, hours: int) -> bool:
        if not value:
            return False
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - parsed <= timedelta(hours=hours)
        except Exception:
            return False

    def _read_jsonl(self, path: Path, limit: int = 200) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        items = []
        for line in lines:
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return items

    def _latest_status_final(self, path: Path) -> str | None:
        if not path.exists():
            return None
        for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]):
            if line.startswith("STATUS_FINAL="):
                return line.split("=", 1)[1].strip()
        return None

    def _grep_tail(self, path: Path, terms: list[str], limit: int = 10) -> list[str]:
        if not path.exists():
            return []
        matches = [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if any(term in line for term in terms)]
        return matches[-limit:]
