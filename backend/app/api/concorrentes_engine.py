from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import require_permission
from app.schemas.concorrente import ConcorrenteAnaliseResponse, ConcorrenteCreate, ConcorrenteEvent, ConcorrenteEventCreate, ConcorrenteHistoricoResponse, ConcorrenteListResponse, ConcorrenteRecord, ConcorrenteUpdate
from app.services.concorrente_engine import LiciConcorrentesEngine

router = APIRouter(prefix='/concorrentes', tags=['LICI Concorrentes Engine'])
engine = LiciConcorrentesEngine()


@router.get('/engine')
def obter_concorrentes_engine(user: dict = Depends(require_permission('dados:ler'))) -> dict[str, object]:
    return engine.info()


@router.get('', response_model=ConcorrenteListResponse)
def listar_concorrentes(user: dict = Depends(require_permission('dados:ler'))) -> ConcorrenteListResponse:
    return engine.list(organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post('/registrar', response_model=ConcorrenteRecord)
def registrar_concorrente(payload: ConcorrenteCreate, user: dict = Depends(require_permission('dados:escrever'))) -> ConcorrenteRecord:
    return engine.registrar(payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get('/analise', response_model=ConcorrenteAnaliseResponse)
def analisar_concorrentes(user: dict = Depends(require_permission('dados:ler'))) -> ConcorrenteAnaliseResponse:
    return engine.analise(organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.patch('/{concorrente_id}', response_model=ConcorrenteRecord)
def atualizar_concorrente(concorrente_id: str, payload: ConcorrenteUpdate, user: dict = Depends(require_permission('dados:escrever'))) -> ConcorrenteRecord:
    return engine.atualizar(concorrente_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post('/{concorrente_id}/arquivar', response_model=ConcorrenteRecord)
def arquivar_concorrente(concorrente_id: str, user: dict = Depends(require_permission('dados:escrever'))) -> ConcorrenteRecord:
    return engine.arquivar(concorrente_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get('/{concorrente_id}', response_model=ConcorrenteRecord)
def obter_concorrente(concorrente_id: str, user: dict = Depends(require_permission('dados:ler'))) -> ConcorrenteRecord:
    return engine.get(concorrente_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.post('/{concorrente_id}/registrar-evento', response_model=ConcorrenteEvent)
def registrar_evento_concorrente(concorrente_id: str, payload: ConcorrenteEventCreate, user: dict = Depends(require_permission('dados:escrever'))) -> ConcorrenteEvent:
    return engine.registrar_evento(concorrente_id, payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get('/{concorrente_id}/historico', response_model=ConcorrenteHistoricoResponse)
def historico_concorrente(concorrente_id: str, user: dict = Depends(require_permission('dados:ler'))) -> ConcorrenteHistoricoResponse:
    return engine.historico(concorrente_id, organization_id=user.get("active_organization_id") or user.get("organization_id"))
