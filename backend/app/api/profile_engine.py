from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_permission
from app.schemas.profile import CurrentProfileResponse, ProfileConfigurationsResponse, ProfileSelectRequest
from app.services.profile_engine import LiciOperationalProfileEngine

router = APIRouter(prefix="/perfil", tags=["LICI Operational Profile Engine"])
engine = LiciOperationalProfileEngine()


@router.get("/engine")
def obter_profile_engine() -> dict[str, object]:
    return engine.info()


@router.get("/atual", response_model=CurrentProfileResponse)
def obter_perfil_atual() -> CurrentProfileResponse:
    return engine.atual()


@router.post("/selecionar", response_model=CurrentProfileResponse)
def selecionar_perfil(payload: ProfileSelectRequest, _: dict = Depends(require_permission("perfil:selecionar"))) -> CurrentProfileResponse:
    return engine.selecionar(payload)


@router.get("/configuracoes", response_model=ProfileConfigurationsResponse)
def obter_configuracoes() -> ProfileConfigurationsResponse:
    return engine.configuracoes()
