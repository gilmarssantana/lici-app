from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from app.core.config import settings
from app.services.audit_log import audit_event


class LiciHealthcheckService:
    def full(self) -> dict[str, Any]:
        components: list[dict[str, Any]] = []
        components.extend(self._configuration_components())
        components.extend(self._http_components())
        components.extend(self._directory_components())
        components.extend(self._json_components())
        components.extend(self._auth_security_components())
        components.append(self._disk_component())
        components.extend(self._backup_components())
        components.extend(self._postgres_components())
        components.extend(self._log_components())
        components.extend(self._systemd_components())

        geral = self._overall_status(components)
        response = {
            "status": geral,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "componentes": components,
        }
        if geral in {"alerta", "erro"}:
            audit_event(
                modulo="healthcheck",
                acao="healthcheck_alerta_erro",
                status=geral,
                detalhes={
                    "componentes_com_problema": [
                        item for item in components if item.get("status") in {"alerta", "erro"}
                    ]
                },
            )
        return response

    def _http_components(self) -> list[dict[str, Any]]:
        checks = [
            ("api_principal", f"{settings.api_url}/health", {200}),
            ("memory_core", f"{settings.memory_core_url}/", {200}),
            ("frontend", f"{settings.frontend_url}/", {200}),
            # Rotas protegidas por JWT podem retornar 401 sem token; isso confirma que a API respondeu.
            ("dashboard", f"{settings.api_url}/dashboard/resumo", {200, 401}),
            ("radar", f"{settings.api_url}/radar/engine", {200, 401}),
            ("triage", f"{settings.api_url}/triagem/engine", {200, 401}),
            ("alertas", f"{settings.api_url}/alertas/engine", {200, 401}),
            ("casos", f"{settings.api_url}/casos/engine", {200, 401}),
            ("scheduler", f"{settings.api_url}/scheduler/status", {200}),
            ("fornecedor_full", f"{settings.api_url}/fornecedor-full/engine", {200, 401}),
            ("consultor_full", f"{settings.api_url}/consultor-full/engine", {200, 401}),
        ]
        return [self._http_check(name, url, expected_codes) for name, url, expected_codes in checks]

    def _configuration_components(self) -> list[dict[str, Any]]:
        components = [
            self._component(
                "config:settings",
                "ok",
                "Configuração central carregada",
                settings.public_snapshot(),
            )
        ]
        app_env = settings.app_root / "config" / "lici.env"
        app_env_example = settings.app_root / "config" / "lici.env.example"
        pg_example = settings.app_root / "config" / "postgres.env.example"
        components.append(self._component(
            "config:lici_env_example",
            "ok" if app_env_example.exists() else "erro",
            "Template versionável existe" if app_env_example.exists() else "Template config/lici.env.example ausente",
            {"path": str(app_env_example)},
        ))
        components.append(self._component(
            "config:postgres_env_example",
            "ok" if pg_example.exists() else "erro",
            "Template PostgreSQL versionável existe" if pg_example.exists() else "Template config/postgres.env.example ausente",
            {"path": str(pg_example)},
        ))
        components.append(self._component(
            "config:lici_env_local",
            "ok" if app_env.exists() else "alerta",
            "Arquivo local config/lici.env encontrado" if app_env.exists() else "Arquivo local config/lici.env ausente; usando defaults seguros",
            {"path": str(app_env)},
        ))
        components.append(self._component(
            "config:postgres_env_local",
            "ok" if settings.postgres_env_file.exists() else "erro",
            "Arquivo secrets/postgres.env encontrado" if settings.postgres_env_file.exists() else "Arquivo secrets/postgres.env ausente",
            {"path": str(settings.postgres_env_file)},
        ))
        ports = [settings.api_port, settings.memory_port, settings.frontend_port, settings.rag_port]
        duplicate_ports = len(set(ports)) != len(ports)
        components.append(self._component(
            "config:ports",
            "erro" if duplicate_ports else "ok",
            "Portas duplicadas na configuração" if duplicate_ports else "Portas internas sem conflito",
            {"api": settings.api_port, "memory": settings.memory_port, "frontend": settings.frontend_port, "rag": settings.rag_port},
        ))
        return components

    def _http_check(self, name: str, url: str, expected_codes: set[int] | None = None) -> dict[str, Any]:
        expected_codes = expected_codes or set(range(200, 300))
        try:
            started = time.perf_counter()
            with urlopen(url, timeout=5) as response:
                status_code = response.status
                ok = status_code in expected_codes
                latency_ms = round((time.perf_counter() - started) * 1000, 2) if "started" in locals() else None
                return self._component(name, "ok" if ok else "erro", f"HTTP {status_code} em {url}", {"url": url, "expected_codes": sorted(expected_codes), "latencia_ms": latency_ms})
        except Exception as exc:
            status_code = getattr(getattr(exc, "fp", None), "status", None) or getattr(exc, "code", None)
            if status_code in expected_codes:
                return self._component(name, "ok", f"HTTP {status_code} esperado em {url}", {"url": url, "expected_codes": sorted(expected_codes)})
            return self._component(name, "erro", f"Falha HTTP em {url}: {exc}", {"url": url, "expected_codes": sorted(expected_codes)})

    def _directory_components(self) -> list[dict[str, Any]]:
        dirs = [
            str(settings.app_root),
            str(settings.docs_root),
            "/root/lici-app/radar",
            "/root/lici-app/triagem",
            "/root/lici-app/alertas",
            "/root/lici-app/casos_vivos",
            "/root/lici-app/scheduler",
            "/root/lici-app/memoria_viva",
            str(settings.backup_root),
            "/root/lici-app/fornecedor_full",
            "/root/lici-app/consultor_full",
            "/root/lici-app/company_documents",
            "/root/lici-app/company_documents/files",
            "/root/lici-app/ia_assistiva",
            "/root/lici-app/auth",
        ]
        components = []
        for path in dirs:
            p = Path(path)
            components.append(
                self._component(
                    f"diretorio:{path}",
                    "ok" if p.is_dir() else "erro",
                    "Diretório existe" if p.is_dir() else "Diretório ausente",
                    {"path": path},
                )
            )
        return components

    def _json_components(self) -> list[dict[str, Any]]:
        files = [
            "/root/lici-app/radar/oportunidades.json",
            "/root/lici-app/triagem/fila.json",
            "/root/lici-app/triagem/logs.json",
            "/root/lici-app/alertas/alertas.json",
            "/root/lici-app/alertas/logs.json",
            "/root/lici-app/casos_vivos/casos.json",
            "/root/lici-app/scheduler/config.json",
            "/root/lici-app/scheduler/logs.json",
            "/root/lici-app/memoria_viva/memorias.json",
            "/root/lici-app/fornecedor_full/records.json",
            "/root/lici-app/consultor_full/records.json",
            "/root/lici-app/consultor_full/leads.json",
            "/root/lici-app/consultor_full/followups.json",
            "/root/lici-app/company_documents/documents.json",
            "/root/lici-app/company_documents/versions.json",
            "/root/lici-app/company_documents/alerts.json",
            "/root/lici-app/ia_assistiva/respostas.json",
            "/root/lici-app/ia_assistiva/telemetria.json",
        ]
        return [self._json_check(path) for path in files]

    def _json_check(self, path: str) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            return self._component(f"json:{path}", "erro", "Arquivo JSON ausente", {"path": path})
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            count = len(data) if isinstance(data, list | dict) else None
            return self._component(f"json:{path}", "ok", "JSON válido", {"path": path, "itens": count})
        except json.JSONDecodeError as exc:
            return self._component(f"json:{path}", "erro", f"JSON inválido: {exc}", {"path": path})

    def _disk_component(self) -> dict[str, Any]:
        usage = shutil.disk_usage("/")
        used_pct = round((usage.used / usage.total) * 100, 2)
        if used_pct >= 90:
            status = "erro"
        elif used_pct >= 80:
            status = "alerta"
        else:
            status = "ok"
        return self._component(
            "espaco_disco:/",
            status,
            f"Uso de disco em {used_pct}%",
            {
                "total_gb": round(usage.total / 1024**3, 2),
                "usado_gb": round(usage.used / 1024**3, 2),
                "livre_gb": round(usage.free / 1024**3, 2),
                "uso_percentual": used_pct,
            },
        )

    def _auth_security_components(self) -> list[dict[str, Any]]:
        checks = [
            (Path("/root/lici-app/auth"), 0o700, "diretorio"),
            (Path("/root/lici-app/auth/usuarios.json"), 0o600, "arquivo"),
            (Path("/root/lici-app/auth/config.json"), 0o600, "arquivo"),
        ]
        components = []
        for path, expected_mode, kind in checks:
            if not path.exists():
                components.append(
                    self._component(
                        f"auth:{path.name or path}",
                        "erro",
                        f"{kind.capitalize()} de autenticação ausente",
                        {"path": str(path), "tipo": kind},
                    )
                )
                continue
            mode = path.stat().st_mode & 0o777
            status = "ok" if mode <= expected_mode else "alerta"
            components.append(
                self._component(
                    f"auth:{path.name or path}",
                    status,
                    f"Permissão {oct(mode)}",
                    {"path": str(path), "tipo": kind, "modo": oct(mode), "modo_maximo_recomendado": oct(expected_mode)},
                )
            )
        bootstrap = Path("/root/lici-app/auth/admin_bootstrap_credentials")
        if bootstrap.exists():
            mode = bootstrap.stat().st_mode & 0o777
            components.append(
                self._component(
                    "auth:admin_bootstrap_credentials",
                    "alerta",
                    "Credencial bootstrap ainda existe; manter protegida e remover após rotação segura.",
                    {"path": str(bootstrap), "modo": oct(mode)},
                )
            )
        else:
            components.append(
                self._component(
                    "auth:admin_bootstrap_credentials",
                    "ok",
                    "Credencial bootstrap ausente.",
                    {"path": str(bootstrap)},
                )
            )
        recovery = Path("/root/lici-app/auth/admin_recovery_credentials")
        if recovery.exists():
            mode = recovery.stat().st_mode & 0o777
            components.append(
                self._component(
                    "auth:admin_recovery_credentials",
                    "alerta",
                    "Credencial de recuperação admin existe; usar para login, rotacionar e remover depois.",
                    {"path": str(recovery), "modo": oct(mode)},
                )
            )
        else:
            components.append(
                self._component(
                    "auth:admin_recovery_credentials",
                    "ok",
                    "Credencial de recuperação admin ausente.",
                    {"path": str(recovery)},
                )
            )
        return components

    def _systemd_components(self) -> list[dict[str, Any]]:
        units = [
            "nginx",
            "lici-api",
            "lici-memory",
            "lici-frontend",
            "lici-healthcheck.timer",
            "lici-scheduler.timer",
            "lici-backup.timer",
            "lici-log-rotate.timer",
        ]
        components = []
        for unit in units:
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", unit],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                state = result.stdout.strip() or result.stderr.strip()
                components.append(
                    self._component(
                        f"systemd:{unit}",
                        "ok" if state == "active" else "erro",
                        f"systemd is-active: {state}",
                        {"unit": unit, "state": state},
                    )
                )
            except (OSError, subprocess.SubprocessError) as exc:
                components.append(self._component(f"systemd:{unit}", "alerta", f"Não foi possível consultar systemd: {exc}", {"unit": unit}))
        return components


    def _backup_components(self) -> list[dict[str, Any]]:
        backup_dir = settings.backup_root
        pg_dir = backup_dir / "postgres"
        components = []
        components.append(self._latest_file_component("backup:archive", backup_dir, "lici-backup-*.tar.gz", max_age_hours=settings.backup_max_age_hours, min_bytes=1024 * 1024))
        components.append(self._latest_file_component("backup:postgres_dump", pg_dir, "lici-*.sql.gz", max_age_hours=settings.backup_max_age_hours, min_bytes=1024))
        manifest = self._latest_file_component("backup:manifest", backup_dir, "lici-backup-*.manifest.json", max_age_hours=settings.backup_max_age_hours, min_bytes=100)
        components.append(manifest)
        latest_manifest = self._latest_file(backup_dir, "lici-backup-*.manifest.json")
        if latest_manifest:
            try:
                data = json.loads(latest_manifest.read_text(encoding="utf-8"))
                archive_path = Path(data.get("archive", {}).get("path", ""))
                pg_path = Path(data.get("postgres_dump", {}).get("path", ""))
                references_exist = archive_path.exists() and pg_path.exists()
                components.append(self._component(
                    "backup:manifest_referencias",
                    "ok" if references_exist else "erro",
                    "Manifesto aponta para archive e dump existentes" if references_exist else "Manifesto aponta para arquivo ausente",
                    {"manifest": str(latest_manifest), "archive": str(archive_path), "postgres_dump": str(pg_path)},
                ))
            except Exception as exc:
                components.append(self._component("backup:manifest_parse", "erro", f"Manifesto inválido: {exc}", {"path": str(latest_manifest)}))
        return components

    def _latest_file_component(self, name: str, directory: Path, pattern: str, max_age_hours: int, min_bytes: int) -> dict[str, Any]:
        latest = self._latest_file(directory, pattern)
        if not latest:
            return self._component(name, "erro", "Nenhum arquivo encontrado", {"directory": str(directory), "pattern": pattern})
        stat = latest.stat()
        age_hours = round((time.time() - stat.st_mtime) / 3600, 2)
        if stat.st_size < min_bytes:
            status = "erro"
            message = f"Arquivo pequeno demais: {stat.st_size} bytes"
        elif age_hours > max_age_hours:
            status = "alerta"
            message = f"Backup antigo: {age_hours}h"
        else:
            status = "ok"
            message = f"Backup recente: {age_hours}h"
        return self._component(name, status, message, {"path": str(latest), "bytes": stat.st_size, "idade_horas": age_hours})

    def _latest_file(self, directory: Path, pattern: str) -> Path | None:
        try:
            files = [path for path in directory.glob(pattern) if path.is_file()]
        except Exception:
            return None
        return max(files, key=lambda path: path.stat().st_mtime) if files else None

    def _postgres_components(self) -> list[dict[str, Any]]:
        dsn = os.getenv("LICI_DATABASE_URL")
        path = settings.postgres_env_file
        if not dsn and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("LICI_DATABASE_URL="):
                    dsn = line.split("=", 1)[1].strip()
                    break
        if not dsn:
            return [self._component("postgres:dsn", "alerta", "LICI_DATABASE_URL não encontrado", {})]
        components = []
        started = time.perf_counter()
        try:
            import psycopg
            with psycopg.connect(dsn, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
                    query_ms = round((time.perf_counter() - started) * 1000, 2)
                    components.append(self._component("postgres:query", "ok" if query_ms < 1000 else "alerta", f"Query simples em {query_ms}ms", {"tempo_query_ms": query_ms}))
                    cur.execute("SELECT pg_database_size(current_database())")
                    size = int(cur.fetchone()[0])
                    components.append(self._component("postgres:tamanho_banco", "ok", f"Banco com {round(size / 1024**2, 2)} MB", {"bytes": size, "mb": round(size / 1024**2, 2)}))
                    for table in [
                        "fornecedor_full_records",
                        "consultor_full_records",
                        "consultor_leads",
                        "consultor_followups",
                        "company_documents",
                        "company_document_versions",
                        "company_document_alerts",
                        "cases",
                        "case_events",
                        "memories",
                        "orgaos",
                        "competitors",
                        "competitor_events",
                    ]:
                        cur.execute("SELECT to_regclass(%s)", (table,))
                        exists = bool(cur.fetchone()[0])
                        components.append(self._component(f"postgres:tabela:{table}", "ok" if exists else "alerta", "Tabela existe" if exists else "Tabela ainda não criada", {"table": table}))
        except Exception as exc:
            components.append(self._component("postgres:query", "erro", f"Falha PostgreSQL: {exc}", {}))
        return components

    def _log_components(self) -> list[dict[str, Any]]:
        files = [
            Path("/root/lici-app/logs/api.jsonl"),
            Path("/root/lici-app/audit/audit.log"),
            Path("/root/lici-app/logs/healthcheck.jsonl"),
        ]
        components = []
        for path in files:
            size = path.stat().st_size if path.exists() else 0
            mb = round(size / 1024**2, 3)
            status = "alerta" if mb >= 50 else "ok"
            components.append(self._component(f"log:{path.name}", status, f"Log com {mb} MB", {"path": str(path), "bytes": size, "mb": mb}))
        return components

    def _overall_status(self, components: list[dict[str, Any]]) -> str:
        statuses = {item["status"] for item in components}
        if "erro" in statuses:
            return "erro"
        if "alerta" in statuses:
            return "alerta"
        return "ok"

    def _component(self, name: str, status: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "nome": name,
            "status": status,
            "mensagem": message,
            "detalhes": details or {},
        }
