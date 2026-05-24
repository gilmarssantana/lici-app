from __future__ import annotations

import json
import os
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from app.services.audit_log import audit_event
from app.services.observability import structured_log

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

CHAT_ROOT = Path("/root/lici-app/chat")
METRICAS_PATH = CHAT_ROOT / "metricas.json"
CONVERSAS_PATH = CHAT_ROOT / "conversas.json"
POSTGRES_ENV_FILE = Path("/root/lici-app/secrets/postgres.env")


class LiciChatTelemetry:
    """Telemetria dual-write do Chat LICI: JSON obrigatório + PostgreSQL quando disponível."""

    def __init__(self, dsn: str | None = None):
        CHAT_ROOT.mkdir(parents=True, exist_ok=True)
        if not METRICAS_PATH.exists():
            self._write_metrics({"metricas": []})
        self.dsn = dsn or os.getenv("LICI_DATABASE_URL") or self._dsn_from_env_file()
        self._pg_ready: bool | None = None

    def ensure_postgres(self) -> bool:
        if not psycopg or not self.dsn:
            return False
        if self._pg_ready is True:
            return True
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS chat_sessions (
                          id TEXT PRIMARY KEY,
                          title TEXT,
                          intent_primary TEXT,
                          user_id TEXT,
                          username TEXT,
                          profile TEXT,
                          operational_profile TEXT,
                          status TEXT DEFAULT 'ativa',
                          message_count INTEGER DEFAULT 0,
                          raw_payload JSONB DEFAULT '{}'::jsonb,
                          created_at TIMESTAMPTZ NOT NULL,
                          updated_at TIMESTAMPTZ NOT NULL
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS chat_messages (
                          id TEXT PRIMARY KEY,
                          session_id TEXT REFERENCES chat_sessions(id) ON DELETE CASCADE,
                          intent TEXT,
                          question TEXT,
                          answer TEXT,
                          found_data BOOLEAN,
                          tools_used JSONB DEFAULT '[]'::jsonb,
                          sources JSONB DEFAULT '[]'::jsonb,
                          user_id TEXT,
                          username TEXT,
                          profile TEXT,
                          endpoint TEXT,
                          response_time_ms NUMERIC,
                          raw_payload JSONB DEFAULT '{}'::jsonb,
                          created_at TIMESTAMPTZ NOT NULL
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS chat_metrics (
                          id TEXT PRIMARY KEY,
                          session_id TEXT,
                          message_id TEXT,
                          intent TEXT,
                          tools_used JSONB DEFAULT '[]'::jsonb,
                          success BOOLEAN,
                          found_data BOOLEAN,
                          response_time_ms NUMERIC,
                          conversation_size INTEGER,
                          user_id TEXT,
                          username TEXT,
                          profile TEXT,
                          operational_profile TEXT,
                          endpoint TEXT,
                          errors JSONB DEFAULT '[]'::jsonb,
                          raw_payload JSONB DEFAULT '{}'::jsonb,
                          created_at TIMESTAMPTZ NOT NULL
                        )
                        """
                    )
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_metrics_created_at ON chat_metrics(created_at DESC)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_metrics_intent ON chat_metrics(intent)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_metrics_session ON chat_metrics(session_id)")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")
            self._pg_ready = True
            return True
        except Exception as exc:
            self._pg_ready = False
            structured_log("api", "chat_postgres_unavailable", "alerta", {"erro": str(exc)})
            return False

    def record_message(
        self,
        *,
        session: dict[str, Any],
        message: dict[str, Any],
        metric: dict[str, Any],
    ) -> dict[str, Any]:
        metric = {"id": metric.get("id") or f"met_{uuid.uuid4().hex[:12]}", **metric}
        metric.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        metric.setdefault("success", not metric.get("errors"))

        data = self._read_metrics()
        data.setdefault("metricas", []).append(metric)
        self._write_metrics(data)
        self._write_postgres(session=session, message=message, metric=metric)
        self._evaluate_alerts(metric)
        return metric

    def metrics_summary(self) -> dict[str, Any]:
        data = self._read_metrics()
        metrics = data.get("metricas", [])
        total = len(metrics)
        success = [m for m in metrics if m.get("success") is True]
        failures = [m for m in metrics if m.get("success") is False or m.get("errors")]
        unanswered = [m for m in metrics if not m.get("found_data")]
        avg_time = round(sum(float(m.get("response_time_ms") or 0) for m in metrics) / total, 2) if total else 0
        sessions = {m.get("session_id") for m in metrics if m.get("session_id")}
        active_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        active_sessions = {
            m.get("session_id") for m in metrics
            if m.get("session_id") and self._parse_dt(m.get("created_at")) >= active_cutoff
        }

        payload = {
            "total_mensagens": total,
            "taxa_sucesso": round((len(success) / total) * 100, 2) if total else 0,
            "total_falhas": len(failures),
            "total_sem_resposta": len(unanswered),
            "tempo_medio_ms": avg_time,
            "sessoes_total": len(sessions),
            "sessoes_ativas_24h": len(active_sessions),
            "top_intencoes": self._top(metrics, "intent"),
            "top_ferramentas": self._top_tools(metrics),
            "perguntas_sem_resposta": [
                {"pergunta": m.get("question"), "intencao": m.get("intent"), "usuario": m.get("username"), "criado_em": m.get("created_at")}
                for m in unanswered[-20:]
            ],
            "uso_por_perfil": self._top(metrics, "operational_profile"),
            "uso_por_usuario": self._top(metrics, "username"),
            "endpoints": self._top(metrics, "endpoint"),
            "erros_recentes": [
                {"session_id": m.get("session_id"), "message_id": m.get("message_id"), "errors": m.get("errors"), "created_at": m.get("created_at")}
                for m in failures[-20:]
            ],
            "alertas_tecnicos": self._technical_alerts(metrics),
            "persistencia": {"json": str(METRICAS_PATH), "postgresql": self.ensure_postgres()},
        }
        return payload

    def record_endpoint_error(self, endpoint: str, user: dict[str, Any] | None, exc: Exception) -> None:
        metric = {
            "id": f"met_{uuid.uuid4().hex[:12]}",
            "session_id": None,
            "message_id": None,
            "intent": "erro_endpoint",
            "tools_used": [],
            "success": False,
            "found_data": False,
            "response_time_ms": 0,
            "conversation_size": 0,
            "user_id": (user or {}).get("id"),
            "username": (user or {}).get("usuario"),
            "profile": (user or {}).get("perfil"),
            "operational_profile": (user or {}).get("perfil_operacional") or (user or {}).get("perfil"),
            "endpoint": endpoint,
            "errors": [str(exc)],
            "question": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data = self._read_metrics()
        data.setdefault("metricas", []).append(metric)
        self._write_metrics(data)
        structured_log("api", "chat_endpoint_failed", "erro", {"endpoint": endpoint, "erro": str(exc), "usuario": metric.get("username")})
        audit_event("chat_engine", "erro_critico_chat", "erro", {"endpoint": endpoint, "erro": str(exc)}, metric.get("session_id"))

    def _write_postgres(self, *, session: dict[str, Any], message: dict[str, Any], metric: dict[str, Any]) -> None:
        if not self.ensure_postgres():
            return
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO chat_sessions (id,title,intent_primary,user_id,username,profile,operational_profile,status,message_count,raw_payload,created_at,updated_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                        ON CONFLICT (id) DO UPDATE SET
                          title=EXCLUDED.title, intent_primary=EXCLUDED.intent_primary, user_id=EXCLUDED.user_id,
                          username=EXCLUDED.username, profile=EXCLUDED.profile, operational_profile=EXCLUDED.operational_profile,
                          status=EXCLUDED.status, message_count=EXCLUDED.message_count, raw_payload=EXCLUDED.raw_payload,
                          updated_at=EXCLUDED.updated_at
                        """,
                        (
                            session["id"], session.get("title"), session.get("intent_primary"), session.get("user_id"), session.get("username"),
                            session.get("profile"), session.get("operational_profile"), session.get("status", "ativa"), session.get("message_count", 0),
                            json.dumps(session, ensure_ascii=False, default=str), session.get("created_at"), session.get("updated_at"),
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO chat_messages (id,session_id,intent,question,answer,found_data,tools_used,sources,user_id,username,profile,endpoint,response_time_ms,raw_payload,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s::jsonb,%s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            message["id"], message.get("session_id"), message.get("intent"), message.get("question"), message.get("answer"),
                            message.get("found_data"), json.dumps(message.get("tools_used", []), ensure_ascii=False), json.dumps(message.get("sources", []), ensure_ascii=False),
                            message.get("user_id"), message.get("username"), message.get("profile"), message.get("endpoint"), message.get("response_time_ms"),
                            json.dumps(message, ensure_ascii=False, default=str), message.get("created_at"),
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO chat_metrics (id,session_id,message_id,intent,tools_used,success,found_data,response_time_ms,conversation_size,user_id,username,profile,operational_profile,endpoint,errors,raw_payload,created_at)
                        VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            metric["id"], metric.get("session_id"), metric.get("message_id"), metric.get("intent"), json.dumps(metric.get("tools_used", []), ensure_ascii=False),
                            metric.get("success"), metric.get("found_data"), metric.get("response_time_ms"), metric.get("conversation_size"), metric.get("user_id"),
                            metric.get("username"), metric.get("profile"), metric.get("operational_profile"), metric.get("endpoint"), json.dumps(metric.get("errors", []), ensure_ascii=False),
                            json.dumps(metric, ensure_ascii=False, default=str), metric.get("created_at"),
                        ),
                    )
        except Exception as exc:
            structured_log("api", "chat_postgres_write_failed", "erro", {"erro": str(exc), "session_id": metric.get("session_id")})
            audit_event("chat_engine", "falha_postgres_metricas", "erro", {"erro": str(exc)}, metric.get("session_id"))

    def _evaluate_alerts(self, metric: dict[str, Any]) -> None:
        if metric.get("errors"):
            structured_log("api", "chat_tool_or_endpoint_failed", "erro", {"errors": metric.get("errors"), "session_id": metric.get("session_id"), "message_id": metric.get("message_id")})
            audit_event("chat_engine", "falha_ferramenta", "erro", {"errors": metric.get("errors"), "tools": metric.get("tools_used")}, metric.get("session_id"))
        if not metric.get("found_data"):
            structured_log("api", "chat_unanswered_question", "alerta", {"intent": metric.get("intent"), "question": metric.get("question"), "session_id": metric.get("session_id")})
        if float(metric.get("response_time_ms") or 0) >= 2000:
            structured_log("api", "chat_slow_response", "alerta", {"response_time_ms": metric.get("response_time_ms"), "session_id": metric.get("session_id")})

        summary = self.metrics_summary_light(window=20)
        if summary["total"] >= 10 and summary["failure_rate"] >= 30:
            structured_log("api", "chat_failure_rate_high", "erro", summary)
            audit_event("chat_engine", "erro_critico_chat", "erro", {"motivo": "taxa_falha_alta", **summary}, metric.get("session_id"))
        if summary["total"] >= 10 and summary["unanswered_rate"] >= 40:
            structured_log("api", "chat_unanswered_rate_high", "alerta", summary)
        if summary["avg_time_ms"] >= 2500:
            structured_log("api", "chat_avg_response_time_high", "alerta", summary)
        if int(metric.get("conversation_size") or 0) >= 50:
            structured_log("api", "chat_anomalous_session", "alerta", {"session_id": metric.get("session_id"), "conversation_size": metric.get("conversation_size")})
            audit_event("chat_engine", "sessao_anomala", "alerta", {"conversation_size": metric.get("conversation_size")}, metric.get("session_id"))

    def metrics_summary_light(self, window: int = 20) -> dict[str, Any]:
        metrics = self._read_metrics().get("metricas", [])[-window:]
        total = len(metrics)
        failures = len([m for m in metrics if not m.get("success") or m.get("errors")])
        unanswered = len([m for m in metrics if not m.get("found_data")])
        avg = round(sum(float(m.get("response_time_ms") or 0) for m in metrics) / total, 2) if total else 0
        return {
            "total": total,
            "failure_rate": round((failures / total) * 100, 2) if total else 0,
            "unanswered_rate": round((unanswered / total) * 100, 2) if total else 0,
            "avg_time_ms": avg,
        }

    def _technical_alerts(self, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
        light = self.metrics_summary_light(window=50)
        alerts = []
        if light["total"] >= 10 and light["failure_rate"] >= 30:
            alerts.append({"tipo": "taxa_falha_alta", "severidade": "erro", **light})
        if light["total"] >= 10 and light["unanswered_rate"] >= 40:
            alerts.append({"tipo": "muitas_perguntas_sem_resposta", "severidade": "alerta", **light})
        if light["avg_time_ms"] >= 2500:
            alerts.append({"tipo": "tempo_medio_alto", "severidade": "alerta", **light})
        endpoint_failures = [m for m in metrics[-50:] if m.get("errors")]
        if endpoint_failures:
            alerts.append({"tipo": "falha_endpoint_ou_ferramenta", "severidade": "alerta", "total": len(endpoint_failures)})
        return alerts

    def _top(self, metrics: list[dict[str, Any]], key: str, limit: int = 10) -> list[dict[str, Any]]:
        counter = Counter(str(m.get(key) or "não_informado") for m in metrics)
        return [{"valor": value, "total": total} for value, total in counter.most_common(limit)]

    def _top_tools(self, metrics: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
        counter: Counter[str] = Counter()
        for m in metrics:
            for tool in m.get("tools_used") or []:
                counter[str(tool)] += 1
        return [{"valor": value, "total": total} for value, total in counter.most_common(limit)]

    def _parse_dt(self, value: str | None) -> datetime:
        if not value:
            return datetime.fromtimestamp(0, timezone.utc)
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return datetime.fromtimestamp(0, timezone.utc)

    def _read_metrics(self) -> dict[str, Any]:
        try:
            return json.loads(METRICAS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"metricas": []}

    def _write_metrics(self, data: dict[str, Any]) -> None:
        CHAT_ROOT.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=CHAT_ROOT, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2, default=str)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(METRICAS_PATH)

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith("LICI_DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except FileNotFoundError:
            return None
        return None
