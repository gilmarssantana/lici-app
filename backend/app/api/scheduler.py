from __future__ import annotations

from fastapi import APIRouter

from app.schemas.scheduler import (
    SchedulerLogsResponse,
    SchedulerRunRequest,
    SchedulerRunResponse,
    SchedulerStatusResponse,
)
from app.services.scheduler import LiciScheduler

router = APIRouter(prefix="/scheduler", tags=["LICI Scheduler"])
scheduler = LiciScheduler()


@router.get("/status", response_model=SchedulerStatusResponse)
def status() -> SchedulerStatusResponse:
    return scheduler.status()


@router.post("/executar-radar", response_model=SchedulerRunResponse)
def executar_radar(payload: SchedulerRunRequest | None = None) -> SchedulerRunResponse:
    return scheduler.executar_radar(payload)


@router.get("/logs", response_model=SchedulerLogsResponse)
def logs() -> SchedulerLogsResponse:
    return scheduler.logs()
