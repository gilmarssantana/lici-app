from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status

from app.services.audit_log import audit_event
from app.services.auth_engine import LiciAuthEngine
from app.services.organization import JsonOrganizationStore

engine = LiciAuthEngine()
org_store = JsonOrganizationStore()


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        audit_event("security", "acesso_negado", "erro", {"motivo": "token_ausente"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token obrigatório")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(
    token: str = Depends(bearer_token),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
) -> dict[str, Any]:
    user = engine.user_from_token(token)
    user = org_store.ensure_user_membership(user)
    if x_organization_id:
        org_store.assert_access(user, x_organization_id, action="selecionar_contexto_http")
        user["organization_id"] = x_organization_id
        user["active_organization_id"] = x_organization_id
        user["organization_role"] = org_store.role_for_user(user, x_organization_id)
    return user


def require_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin(user):
        audit_event(
            "security",
            "acesso_negado",
            "erro",
            {"motivo": "admin_necessario", "usuario": user.get("usuario"), "perfil": user.get("perfil")},
            user.get("id"),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão de administrador necessária")
    return user


def require_permission(*required_permissions: str) -> Callable[[Request, dict[str, Any]], dict[str, Any]]:
    def dependency(request: Request, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if has_permission(user, *required_permissions):
            return user
        audit_event(
            "security",
            "acesso_negado",
            "erro",
            {
                "motivo": "permissao_insuficiente",
                "path": str(request.url.path),
                "method": request.method,
                "usuario": user.get("usuario"),
                "perfil": user.get("perfil"),
                "necessarias": list(required_permissions),
                "permissoes_usuario": user.get("permissoes", []),
            },
            user.get("id"),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente")

    return dependency


def has_permission(user: dict[str, Any], *required_permissions: str) -> bool:
    if _is_admin(user):
        return True
    permissions = set(user.get("permissoes") or []) | set(user.get("organization_permissions") or [])
    if "*" in permissions:
        return True
    if any(permission in permissions for permission in required_permissions):
        return True
    # Perfil leitura pode acessar rotas marcadas como leitura quando possuir dados:ler.
    if "dados:ler" in permissions and any(permission.endswith(":ler") for permission in required_permissions):
        return True
    return False


def _is_admin(user: dict[str, Any]) -> bool:
    permissions = set(user.get("permissoes") or [])
    return user.get("perfil") == "admin" or "auth:admin" in permissions or "*" in permissions
