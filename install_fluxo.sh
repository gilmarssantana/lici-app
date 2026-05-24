#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/root/lici-app"
BACKEND="$APP_ROOT/backend"
cd "$BACKEND"

echo "==> Criando módulo app/fluxo..."
mkdir -p app/fluxo

cat > app/fluxo/__init__.py <<'PY'
from .router import router
PY

cat > app/fluxo/router.py <<'PY'
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/fluxo", tags=["Fluxo Orchestrator"])

@router.get("/status")
def fluxo_status():
    return {
        "ok": True,
        "service": "Fluxo Orchestrator",
        "status": "online",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
PY

MAIN_FILE=""
if [ -f app/main.py ]; then
  MAIN_FILE="app/main.py"
elif [ -f main.py ]; then
  MAIN_FILE="main.py"
else
  echo "ERRO: não encontrei app/main.py nem main.py"
  exit 1
fi

echo "==> Main detectado: $MAIN_FILE"
cp "$MAIN_FILE" "$MAIN_FILE.bak.$(date +%Y%m%d%H%M%S)"

if ! grep -q "from app.fluxo.router import router as fluxo_router" "$MAIN_FILE"; then
  sed -i '1ifrom app.fluxo.router import router as fluxo_router' "$MAIN_FILE"
fi

if ! grep -q "include_router(fluxo_router)" "$MAIN_FILE"; then
  cat >> "$MAIN_FILE" <<'PY'

# Fluxo Orchestrator
app.include_router(fluxo_router)
PY
fi

echo "==> Testando import Python..."
python3 -m py_compile app/fluxo/router.py "$MAIN_FILE"

echo "==> Reiniciando backend..."
if systemctl list-units --type=service --all | grep -qi "lici"; then
  systemctl restart "$(systemctl list-units --type=service --all | awk '/lici/ {print $1; exit}')"
elif systemctl list-units --type=service --all | grep -qi "backend"; then
  systemctl restart "$(systemctl list-units --type=service --all | awk '/backend/ {print $1; exit}')"
else
  echo "AVISO: serviço systemd do backend não detectado. Reinicie o backend manualmente."
fi

sleep 2

echo "==> Testando endpoint..."
curl -s http://127.0.0.1:8100/fluxo/status || true
echo
echo "==> Instalação concluída."
