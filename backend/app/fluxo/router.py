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
