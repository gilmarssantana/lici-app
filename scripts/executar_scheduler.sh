#!/usr/bin/env bash
set -Eeuo pipefail

LOG_FILE="/root/lici-app/scheduler/cron.log"
OBS_LOG_DIR="/root/lici-app/logs"
ENDPOINT="http://127.0.0.1:8100/scheduler/executar-radar"

mkdir -p "$(dirname "$LOG_FILE")" "$OBS_LOG_DIR"

structured_log() {
  local status="$1"
  local event="$2"
  local details="$3"
  PYTHONPATH=/root/lici-app/backend /root/lici-app/backend/venv/bin/python - "$status" "$event" "$details" <<'PY' || true
import json, sys
from app.services.observability import structured_log
status, event, details = sys.argv[1:4]
try:
    parsed = json.loads(details)
except Exception:
    parsed = {"mensagem": details}
structured_log("scheduler", event, status, parsed)
PY
}

status=ok
started=$(date -Is)
response_file=$(mktemp)
http_code=000
{
  echo "==== $started | LICI Scheduler start ===="
  if http_code=$(curl --silent --show-error \
    --output "$response_file" \
    --write-out '%{http_code}' \
    --request POST "$ENDPOINT" \
    --header 'Content-Type: application/json' \
    --data '{}'); then
    cat "$response_file"
    echo
    if [[ ! "$http_code" =~ ^2 ]]; then
      status=erro
    fi
  else
    status=erro
  fi
  echo "HTTP_CODE=$http_code"
  echo "==== $(date -Is) | LICI Scheduler end ===="
} >> "$LOG_FILE" 2>&1

structured_log "$status" "scheduler_run" "{\"endpoint\":\"$ENDPOINT\",\"http_code\":\"$http_code\",\"started_at\":\"$started\"}"
rm -f "$response_file"

if [[ "$status" != "ok" ]]; then
  exit 1
fi
