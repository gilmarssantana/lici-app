from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, status

from app.api.security import engine, get_current_user, require_admin
from app.schemas.auth import (
    AuthChangeProfileRequest,
    AuthLoginRequest,
    AuthMeResponse,
    AuthMessageResponse,
    AuthTokenResponse,
    AuthUserCreateRequest,
    AuthUserResponse,
    AuthUsersListResponse,
)
from fastapi import Depends

router = APIRouter(prefix="/auth", tags=["LICI Auth Engine"])


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: AuthLoginRequest) -> dict:
    return engine.login(payload)


@router.get("/me", response_model=AuthMeResponse)
def me(user: dict = Depends(get_current_user)) -> dict:
    return {"usuario": engine.public_user(user)}


@router.post("/usuarios", response_model=AuthUserResponse)
def criar_usuario(payload: AuthUserCreateRequest, token: str | None = Header(default=None, alias="Authorization")) -> dict:
    # Bootstrap seguro: o primeiro usuário pode ser criado sem JWT,
    # porque o acesso público ainda está protegido pelo Basic Auth do Nginx.
    if engine.bootstrap_allowed():
        if payload.perfil != "admin":
            payload = payload.model_copy(update={"perfil": "admin"})
        return engine.create_user(payload, actor=None)

    if not token or not token.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token obrigatório para criar novos usuários")
    actor = engine.user_from_token(token.split(" ", 1)[1].strip())
    engine.require_admin(actor)
    return engine.create_user(payload, actor=actor)


@router.get("/usuarios", response_model=AuthUsersListResponse)
def listar_usuarios(_: dict = Depends(require_admin)) -> dict:
    return engine.list_users()


@router.post("/usuarios/{user_id}/alterar-perfil", response_model=AuthUserResponse)
def alterar_perfil(user_id: str, payload: AuthChangeProfileRequest, actor: dict = Depends(require_admin)) -> dict:
    return engine.change_profile(user_id, payload, actor)


@router.post("/usuarios/{user_id}/desativar", response_model=AuthMessageResponse)
def desativar_usuario(user_id: str, actor: dict = Depends(require_admin)) -> dict:
    user = engine.deactivate_user(user_id, actor)
    return {"status": "ok", "mensagem": "Usuário desativado", "usuario": user}
