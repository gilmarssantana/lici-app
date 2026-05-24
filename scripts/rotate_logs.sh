#!/usr/bin/env bash
set -Eeuo pipefail

MAX_BYTES="${LICI_LOG_MAX_BYTES:-10485760}"
KEEP="${LICI_LOG_KEEP:-14}"
OBS_LOG_DIR="/root/lici-app/logs"

mkdir -p "$OBS_LOG_DIR"

rotate_one() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  local size
  size=$(stat -c '%s' "$file" 2>/dev/null || echo 0)
  [[ "$size" -ge "$MAX_BYTES" ]] || return 0

  rm -f "${file}.${KEEP}.gz"
  local i
  for (( i=KEEP-1; i>=1; i-- )); do
    if [[ -f "${file}.${i}.gz" ]]; then
      mv "${file}.${i}.gz" "${file}.$((i+1)).gz"
    fi
  done
  gzip -c "$file" > "${file}.1.gz"
  : > "$file"
}

for file in \
  /root/lici-app/logs/*.jsonl \
  /root/lici-app/health/*.log \
  /root/lici-app/scheduler/*.log \
  /root/backups/lici/*.log; do
  rotate_one "$file"
done

PYTHONPATH=/root/lici-app/backend /root/lici-app/backend/venv/bin/python - <<'PY' || true
from app.services.observability import structured_log
structured_log('api', 'log_rotation_run', 'ok', {'max_bytes': 10485760, 'keep': 14, 'strategy': 'internal_script'})
PY
