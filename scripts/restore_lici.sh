#!/usr/bin/env bash
set -Eeuo pipefail

MODE="dry-run"
ARCHIVE=""
PG_DUMP=""
TARGET_ROOT="/"
POSTGRES_ENV="/root/lici-app/secrets/postgres.env"

usage() {
  cat <<'EOF'
Uso:
  scripts/restore_lici.sh --archive /root/backups/lici/lici-backup-YYYYmmdd-HHMM.tar.gz --pg-dump /root/backups/lici/postgres/lici-YYYYmmdd-HHMM.sql.gz
  CONFIRM_RESTORE_LICI=YES scripts/restore_lici.sh --apply --archive ... --pg-dump ...

Comportamento:
  - Por padrão roda em dry-run: valida arquivos, lista conteúdo e mostra o plano.
  - --apply exige CONFIRM_RESTORE_LICI=YES.
  - Restauração real para serviços em execução é operação sensível; usar em VPS nova ou janela controlada.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) MODE="apply"; shift ;;
    --dry-run) MODE="dry-run"; shift ;;
    --archive) ARCHIVE="${2:-}"; shift 2 ;;
    --pg-dump) PG_DUMP="${2:-}"; shift 2 ;;
    --target-root) TARGET_ROOT="${2:-/}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Argumento inválido: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$ARCHIVE" || -z "$PG_DUMP" ]]; then
  echo "ERRO: informe --archive e --pg-dump." >&2
  usage
  exit 2
fi

if [[ ! -f "$ARCHIVE" ]]; then
  echo "ERRO: archive não encontrado: $ARCHIVE" >&2
  exit 1
fi

if [[ ! -f "$PG_DUMP" ]]; then
  echo "ERRO: dump PostgreSQL não encontrado: $PG_DUMP" >&2
  exit 1
fi

echo "Validando gzip do dump..."
gunzip -t "$PG_DUMP"

echo "Validando tar.gz..."
tar -tzf "$ARCHIVE" >/tmp/lici-restore-contents.txt

echo "Resumo do backup:"
du -h "$ARCHIVE" "$PG_DUMP"
echo
echo "Primeiros itens do archive:"
sed -n '1,40p' /tmp/lici-restore-contents.txt

echo
echo "Plano de restauração:"
echo "1. Parar serviços: lici-api, lici-memory, lici-frontend, nginx."
echo "2. Extrair archive em: $TARGET_ROOT"
echo "3. Restaurar PostgreSQL a partir de: $PG_DUMP"
echo "4. Recarregar systemd e iniciar serviços."
echo "5. Rodar /root/lici-app/scripts/healthcheck_lici.sh e GET /health/full."

if [[ "$MODE" != "apply" ]]; then
  echo
  echo "DRY-RUN concluído. Nada foi alterado."
  exit 0
fi

if [[ "${CONFIRM_RESTORE_LICI:-}" != "YES" ]]; then
  echo "ERRO: para aplicar, defina CONFIRM_RESTORE_LICI=YES." >&2
  exit 1
fi

if [[ ! -f "$POSTGRES_ENV" ]]; then
  echo "ERRO: arquivo PostgreSQL ausente: $POSTGRES_ENV" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$POSTGRES_ENV"
if [[ -z "${LICI_DATABASE_URL:-}" ]]; then
  echo "ERRO: LICI_DATABASE_URL ausente em $POSTGRES_ENV" >&2
  exit 1
fi

echo "Parando serviços..."
systemctl stop lici-api lici-memory lici-frontend nginx || true

echo "Extraindo archive..."
tar -xzf "$ARCHIVE" -C "$TARGET_ROOT"

echo "Restaurando PostgreSQL..."
gunzip -c "$PG_DUMP" | psql "$LICI_DATABASE_URL"

echo "Recarregando systemd e iniciando serviços..."
systemctl daemon-reload
systemctl start nginx lici-memory lici-api lici-frontend

echo "Rodando healthcheck..."
/root/lici-app/scripts/healthcheck_lici.sh

echo "Restauração concluída."
