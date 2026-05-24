from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_permission
from app.schemas.consultor import (
    ConsultorClienteCreate,
    ConsultorClienteDetalheResponse,
    ConsultorClienteRecord,
    ConsultorClientesResponse,
    ConsultorDemandaCreate,
    ConsultorDemandaRecord,
    ConsultorDemandasResponse,
    ConsultorDemandaStatusUpdate,
)
from app.services.consultor_engine import LiciConsultorEngine

router = APIRouter(prefix="/consultor", tags=["LICI Consultor Engine"])
engine = LiciConsultorEngine()


@router.get("/engine")
def obter_consultor_engine(_: dict = Depends(require_permission("consultor:ler"))) -> dict[str, object]:
    return engine.info()


@router.get("/clientes", response_model=ConsultorClientesResponse)
def listar_clientes(user: dict = Depends(require_permission("consultor:ler"))) -> ConsultorClientesResponse:
    return engine.list_clientes(organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/clientes", response_model=ConsultorClienteRecord)
def criar_cliente(payload: ConsultorClienteCreate, user: dict = Depends(require_permission("consultor:escrever"))) -> ConsultorClienteRecord:
    return engine.create_cliente(payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/clientes/{cliente_id}", response_model=ConsultorClienteDetalheResponse)
def obter_cliente(cliente_id: str, user: dict = Depends(require_permission("consultor:ler"))) -> ConsultorClienteDetalheResponse:
    return engine.get_cliente(cliente_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/clientes/{cliente_id}/registrar-demanda", response_model=ConsultorDemandaRecord)
def registrar_demanda(cliente_id: str, payload: ConsultorDemandaCreate, user: dict = Depends(require_permission("consultor:escrever"))) -> ConsultorDemandaRecord:
    return engine.registrar_demanda(cliente_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/demandas", response_model=ConsultorDemandasResponse)
def listar_demandas(user: dict = Depends(require_permission("consultor:ler"))) -> ConsultorDemandasResponse:
    return engine.list_demandas(organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post("/demandas/{demanda_id}/atualizar-status", response_model=ConsultorDemandaRecord)
def atualizar_status_demanda(demanda_id: str, payload: ConsultorDemandaStatusUpdate, user: dict = Depends(require_permission("consultor:escrever"))) -> ConsultorDemandaRecord:
    return engine.atualizar_status_demanda(demanda_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))
