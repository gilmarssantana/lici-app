from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.security import get_current_user, require_admin, require_permission
from app.schemas.organization import (
    OrganizationContextResponse,
    OrganizationCreateRequest,
    OrganizationMembershipRequest,
    OrganizationMembershipResponse,
    OrganizationResponse,
    OrganizationSwitchRequest,
)
from app.services.organization import JsonOrganizationStore

router = APIRouter(prefix="/organizacoes", tags=["LICI Organizações"])
store = JsonOrganizationStore()


@router.get("/contexto", response_model=OrganizationContextResponse)
def contexto_organizacional(user: dict = Depends(get_current_user)) -> dict:
    user = store.enrich_user(user)
    return {
        "active_organization_id": user["active_organization_id"],
        "organization_role": user["organization_role"],
        "organizations": user["organizations"],
        "active_users": store.active_users(),
    }


@router.get("", response_model=list[OrganizationResponse])
def listar_organizacoes(_: dict = Depends(require_permission("org:ler", "dados:ler"))) -> list[dict]:
    return store.list_organizations()


@router.post("", response_model=OrganizationResponse)
def criar_organizacao(payload: OrganizationCreateRequest, actor: dict = Depends(require_admin)) -> dict:
    return store.create_organization(payload.nome, payload.slug, actor=actor)


@router.post("/usuarios", response_model=OrganizationMembershipResponse)
def vincular_usuario(payload: OrganizationMembershipRequest, actor: dict = Depends(require_admin)) -> dict:
    return store.upsert_membership(payload.user_id, payload.organization_id, payload.role, actor=actor)


@router.post("/trocar", response_model=OrganizationContextResponse)
def trocar_organizacao(payload: OrganizationSwitchRequest, user: dict = Depends(get_current_user)) -> dict:
    user = store.switch_active_organization(user, payload.organization_id)
    return {
        "active_organization_id": user["active_organization_id"],
        "organization_role": user["organization_role"],
        "organizations": user["organizations"],
        "active_users": store.active_users(),
    }
