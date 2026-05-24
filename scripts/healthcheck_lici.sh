#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${LICI_APP_ROOT:-/root/lici-app}"
APP_ENV="$APP_ROOT/config/lici.env"
if [[ -f "$APP_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$APP_ENV"
fi

LOG_DIR="$APP_ROOT/health"
LOG_FILE="$LOG_DIR/healthcheck.log"
AUDIT_LOG="${LICI_AUDIT_LOG:-/root/lici-app/audit/audit.log}"
OBS_LOG_DIR="${LICI_LOGS_ROOT:-/root/lici-app/logs}"
NGINX_PUBLIC_URL="${LICI_PUBLIC_URL:-https://licitaprobrasil.com/}"
NGINX_RESOLVE="${LICI_PUBLIC_DOMAIN:-licitaprobrasil.com}:443:127.0.0.1"
mkdir -p "$LOG_DIR" "$(dirname "$AUDIT_LOG")" "$OBS_LOG_DIR"

audit_event() {
  local status_text="$1"
  local details="$2"
  python3 - "$AUDIT_LOG" "$status_text" "$details" <<'PYAUDIT' || true
import json, sys, uuid
from datetime import datetime, timezone
path, status, details = sys.argv[1:4]
event = {
    "id": str(uuid.uuid4()),
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "modulo": "healthcheck",
    "acao": "execucao_healthcheck_systemd",
    "status": status,
    "detalhes": {"mensagem": details},
    "id_relacionado": "lici-healthcheck.service",
}
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")
PYAUDIT
}

structured_log() {
  local status_text="$1"
  local event="$2"
  local details="$3"
  PYTHONPATH="$APP_ROOT/backend" "$APP_ROOT/backend/venv/bin/python" - "$status_text" "$event" "$details" <<'PY' || true
import json, sys
from app.services.observability import structured_log
status, event, details = sys.argv[1:4]
try:
    parsed = json.loads(details)
except Exception:
    parsed = {"mensagem": details}
structured_log("healthcheck", event, status, parsed)
PY
}

check_service() {
  local unit="$1"
  local attempts="${2:-5}"
  local delay="${3:-2}"
  local state="unknown"
  for ((i=1; i<=attempts; i++)); do
    if systemctl is-active --quiet "$unit"; then
      echo "OK systemd $unit active"
      return 0
    fi
    state=$(systemctl is-active "$unit" || true)
    if [[ "$state" == "activating" && "$i" -lt "$attempts" ]]; then
      sleep "$delay"
      continue
    fi
    if [[ "$i" -lt "$attempts" ]]; then
      sleep "$delay"
    fi
  done
  echo "ERRO systemd $unit inactive: $state"
  return 1
}

check_http() {
  local name="$1"
  local url="$2"
  local attempts="${3:-5}"
  local delay="${4:-2}"
  local code="000"
  for ((i=1; i<=attempts; i++)); do
    code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$url" || true)
    if [[ "$code" =~ ^(2|3) ]]; then
      echo "OK http $name $url -> $code"
      return 0
    fi
    if [[ "$i" -lt "$attempts" ]]; then
      sleep "$delay"
    fi
  done
  echo "ERRO http $name $url -> $code"
  return 1
}

status=0
{
  echo "==== $(date -Is) | LICI healthcheck start ===="

  check_service nginx || status=1
  check_service lici-api || status=1
  check_service lici-memory || status=1
  check_service lici-frontend || status=1
  check_service lici-scheduler.timer || status=1
  check_service lici-backup.timer || status=1
  check_service postgresql || status=1

  if command -v pg_isready >/dev/null 2>&1; then
    if pg_isready >/dev/null 2>&1; then
      echo "OK postgresql pg_isready accepting connections"
    else
      echo "ERRO postgresql pg_isready falhou"
      status=1
    fi
  else
    echo "ALERTA pg_isready não encontrado; validação PostgreSQL limitada ao systemd"
  fi

  root_code=$(curl -k -sS -o /dev/null -w '%{http_code}' -I --resolve "$NGINX_RESOLVE" --max-time 10 "$NGINX_PUBLIC_URL" || true)
  if [[ "$root_code" == "401" ]]; then
    echo "OK nginx HTTPS protegido por Basic Auth -> 401 sem credenciais"
  else
    echo "ALERTA nginx HTTPS sem credenciais retornou $root_code; verificar proteção pública"
    status=1
  fi

  check_http api_health "http://${LICI_API_HOST:-127.0.0.1}:${LICI_API_PORT:-8100}/health" || status=1
  check_http api_health_full "http://${LICI_API_HOST:-127.0.0.1}:${LICI_API_PORT:-8100}/health/full" || status=1
  check_http memory_core "http://${LICI_MEMORY_HOST:-127.0.0.1}:${LICI_MEMORY_PORT:-8010}/" || status=1
  check_http frontend "http://${LICI_FRONTEND_HOST:-127.0.0.1}:${LICI_FRONTEND_PORT:-5173}" || status=1

  df -h /
  echo "STATUS_FINAL=$([[ $status -eq 0 ]] && echo OK || echo ALERTA)"
  echo "==== $(date -Is) | LICI healthcheck end ===="
} >> "$LOG_FILE" 2>&1

if [[ "$status" -eq 0 ]]; then
  audit_event "ok" "healthcheck systemd OK"
  structured_log "ok" "healthcheck_run" "{\"status_final\":\"OK\",\"log_legado\":\"$LOG_FILE\"}"
else
  audit_event "erro" "healthcheck systemd retornou ALERTA; consultar $LOG_FILE"
  structured_log "erro" "healthcheck_error" "{\"status_final\":\"ALERTA\",\"log_legado\":\"$LOG_FILE\"}"
fi

exit "$status"
