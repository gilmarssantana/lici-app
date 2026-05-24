#!/usr/bin/env bash
set -Eeuo pipefail

APP_ROOT="${LICI_APP_ROOT:-/root/lici-app}"
APP_ENV="$APP_ROOT/config/lici.env"
if [[ -f "$APP_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$APP_ENV"
fi

BACKUP_DIR="${LICI_BACKUP_ROOT:-/root/backups/lici}"
POSTGRES_BACKUP_DIR="$BACKUP_DIR/postgres"
STAMP="$(date +%Y%m%d-%H%M)"
ARCHIVE="$BACKUP_DIR/lici-backup-$STAMP.tar.gz"
PG_DUMP_FILE="$POSTGRES_BACKUP_DIR/lici-$STAMP.sql.gz"
MANIFEST="$BACKUP_DIR/lici-backup-$STAMP.manifest.json"
LOG_FILE="$BACKUP_DIR/backup.log"
AUDIT_LOG="${LICI_AUDIT_LOG:-/root/lici-app/audit/audit.log}"
POSTGRES_ENV="${LICI_SECRETS_ROOT:-/root/lici-app/secrets}/postgres.env"
OBS_LOG_DIR="${LICI_LOGS_ROOT:-/root/lici-app/logs}"
KEEP_COUNT="${LICI_BACKUP_KEEP_COUNT:-7}"

mkdir -p "$BACKUP_DIR" "$POSTGRES_BACKUP_DIR" "$(dirname "$AUDIT_LOG")" "$OBS_LOG_DIR"

audit_event() {
  local status="$1"
  local details="$2"
  python3 - "$AUDIT_LOG" "$status" "$details" "$ARCHIVE" "$PG_DUMP_FILE" <<'PY'
import json, sys, uuid
from datetime import datetime, timezone
path, status, details, archive, pg_dump_file = sys.argv[1:6]
event = {
    "id": str(uuid.uuid4()),
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "modulo": "backup",
    "acao": "execucao_backup",
    "status": status,
    "detalhes": {"mensagem": details, "arquivo": archive, "postgres_dump": pg_dump_file},
    "id_relacionado": archive,
}
with open(path, "a", encoding="utf-8") as f:
    f.write(json.dumps(event, ensure_ascii=False) + "\n")
PY
}

write_manifest() {
  python3 - "$ARCHIVE" "$PG_DUMP_FILE" "$MANIFEST" <<'PY'
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

archive, pg_dump, manifest = [Path(arg) for arg in sys.argv[1:4]]

def file_info(path: Path) -> dict:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": h.hexdigest(),
    }

data = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "host": os.uname().nodename,
    "archive": file_info(archive),
    "postgres_dump": file_info(pg_dump),
    "restore_hint": "/root/lici-app/scripts/restore_lici.sh --archive {archive} --pg-dump {pg_dump}",
    "contains_sensitive_data": True,
    "sensitive_note": "Backup contém dados operacionais, documentos e segredos locais. Não enviar para Git público.",
}
manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.chmod(manifest, 0o600)
PY
}

structured_log() {
  local status="$1"
  local event="$2"
  local details="$3"
  PYTHONPATH="$APP_ROOT/backend" "$APP_ROOT/backend/venv/bin/python" - "$status" "$event" "$details" <<'PY' || true
import json, sys
from app.services.observability import structured_log
status, event, details = sys.argv[1:4]
try:
    parsed = json.loads(details)
except Exception:
    parsed = {"mensagem": details}
structured_log("backup", event, status, parsed)
PY
}

trap 'code=$?; audit_event "erro" "backup falhou com exit code ${code}"; structured_log "erro" "backup_failed" "{\"exit_code\":${code},\"arquivo\":\"${ARCHIVE}\",\"postgres_dump\":\"${PG_DUMP_FILE}\"}"; exit $code' ERR

INCLUDES=(
  "$APP_ROOT"
  "${LICI_DOCS_ROOT:-/root/lici-docs}"
  "/root/agente-licitacoes"
  "/etc/nginx/sites-available/lici"
  "$PG_DUMP_FILE"
)

for item in /etc/systemd/system/lici-*.service /etc/systemd/system/lici-*.timer; do
  if [[ -e "$item" ]]; then
    INCLUDES+=("$item")
  fi
done

{
  echo "==== $(date -Is) | LICI backup start ===="
  echo "Arquivo: $ARCHIVE"
  echo "PostgreSQL dump: $PG_DUMP_FILE"

  if [[ ! -f "$POSTGRES_ENV" ]]; then
    echo "ERRO: arquivo de ambiente PostgreSQL não encontrado: $POSTGRES_ENV"
    exit 1
  fi

  # shellcheck disable=SC1090
  source "$POSTGRES_ENV"

  if [[ -z "${LICI_DATABASE_URL:-}" ]]; then
    echo "ERRO: LICI_DATABASE_URL ausente em $POSTGRES_ENV"
    exit 1
  fi

  if ! command -v pg_dump >/dev/null 2>&1; then
    echo "ERRO: pg_dump não encontrado"
    exit 1
  fi

  echo "Gerando pg_dump do banco lici..."
  pg_dump --no-owner --no-privileges --dbname="$LICI_DATABASE_URL" | gzip -c > "$PG_DUMP_FILE"
  chmod 600 "$PG_DUMP_FILE"

  echo "Validando dump gzip..."
  gunzip -t "$PG_DUMP_FILE"

  echo "Validando conteúdo SQL do dump..."
  DUMP_SAMPLE="$(mktemp)"
  gunzip -c "$PG_DUMP_FILE" > "$DUMP_SAMPLE"
  if ! grep -qE 'CREATE TABLE|COPY public\.|PostgreSQL database dump' "$DUMP_SAMPLE"; then
    rm -f "$DUMP_SAMPLE"
    echo "ERRO: dump PostgreSQL parece inválido ou vazio"
    exit 1
  fi
  rm -f "$DUMP_SAMPLE"

  echo "Dump PostgreSQL criado: $(du -h "$PG_DUMP_FILE" | awk '{print $1}')"

  tar \
    --ignore-failed-read \
    --warning=no-file-changed \
    --exclude="$APP_ROOT/frontend/node_modules" \
    --exclude="$APP_ROOT/frontend/dist" \
    --exclude="$APP_ROOT/backend/.venv" \
    --exclude="$APP_ROOT/backend/venv" \
    --exclude='/root/agente-licitacoes/venv' \
    --exclude='/root/agente-licitacoes/.venv' \
    --exclude='/root/agente-licitacoes/__pycache__' \
    --exclude="$APP_ROOT/.lici_basic_auth_credentials" \
    -czf "$ARCHIVE" \
    "${INCLUDES[@]}"

  chmod 600 "$ARCHIVE"
  echo "Backup criado: $(du -h "$ARCHIVE" | awk '{print $1}')"

  echo "Gerando manifesto verificável..."
  write_manifest
  echo "Manifesto criado: $MANIFEST"

  mapfile -t old_backups < <(ls -1t "$BACKUP_DIR"/lici-backup-*.tar.gz 2>/dev/null | tail -n +"$((KEEP_COUNT + 1))")
  if (( ${#old_backups[@]} > 0 )); then
    printf 'Removendo backups antigos:\n'
    printf ' - %s\n' "${old_backups[@]}"
    rm -f "${old_backups[@]}"
  fi

  mapfile -t old_pg_dumps < <(ls -1t "$POSTGRES_BACKUP_DIR"/lici-*.sql.gz 2>/dev/null | tail -n +"$((KEEP_COUNT + 1))")
  if (( ${#old_pg_dumps[@]} > 0 )); then
    printf 'Removendo dumps PostgreSQL antigos:\n'
    printf ' - %s\n' "${old_pg_dumps[@]}"
    rm -f "${old_pg_dumps[@]}"
  fi

  mapfile -t old_manifests < <(ls -1t "$BACKUP_DIR"/lici-backup-*.manifest.json 2>/dev/null | tail -n +"$((KEEP_COUNT + 1))")
  if (( ${#old_manifests[@]} > 0 )); then
    printf 'Removendo manifestos antigos:\n'
    printf ' - %s\n' "${old_manifests[@]}"
    rm -f "${old_manifests[@]}"
  fi

  echo "Backups mantidos: $(ls -1 "$BACKUP_DIR"/lici-backup-*.tar.gz 2>/dev/null | wc -l)"
  echo "Dumps PostgreSQL mantidos: $(ls -1 "$POSTGRES_BACKUP_DIR"/lici-*.sql.gz 2>/dev/null | wc -l)"
  echo "Manifestos mantidos: $(ls -1 "$BACKUP_DIR"/lici-backup-*.manifest.json 2>/dev/null | wc -l)"
  echo "==== $(date -Is) | LICI backup end ===="
} >> "$LOG_FILE" 2>&1

audit_event "ok" "backup criado com sucesso"
structured_log "ok" "backup_run" "{\"arquivo\":\"$ARCHIVE\",\"postgres_dump\":\"$PG_DUMP_FILE\",\"manifesto\":\"$MANIFEST\",\"backups_mantidos\":$(ls -1 "$BACKUP_DIR"/lici-backup-*.tar.gz 2>/dev/null | wc -l),\"dumps_postgres_mantidos\":$(ls -1 "$POSTGRES_BACKUP_DIR"/lici-*.sql.gz 2>/dev/null | wc -l),\"manifestos_mantidos\":$(ls -1 "$BACKUP_DIR"/lici-backup-*.manifest.json 2>/dev/null | wc -l)}"
