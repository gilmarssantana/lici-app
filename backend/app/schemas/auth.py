from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.organization import OrganizationResponse, OrganizationRole

UserProfile = Literal["admin", "consultor", "fornecedor", "comprador", "leitura"]
UserStatus = Literal["ativo", "inativo"]


class AuthLoginRequest(BaseModel):
    usuario: str = Field(..., min_length=3, max_length=120)
    senha: str = Field(..., min_length=6, max_length=256)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: "AuthUserResponse"


class AuthUserCreateRequest(BaseModel):
    usuario: str = Field(..., min_length=3, max_length=120)
    nome: str = Field(..., min_length=2, max_length=160)
    senha: str = Field(..., min_length=8, max_length=256)
    perfil: UserProfile = "fornecedor"
    permissoes: list[str] | None = None
    organization_id: str | None = None
    organization_role: OrganizationRole | None = None


class AuthChangeProfileRequest(BaseModel):
    perfil: UserProfile
    permissoes: list[str] | None = None


class AuthUserResponse(BaseModel):
    id: str
    usuario: str
    nome: str
    perfil: UserProfile
    perfil_operacional: str
    permissoes: list[str]
    status: UserStatus
    organization_id: str | None = None
    active_organization_id: str | None = None
    organization_role: OrganizationRole | None = None
    organization_ids: list[str] = Field(default_factory=list)
    organizations: list[OrganizationResponse] = Field(default_factory=list)
    organization_permissions: list[str] = Field(default_factory=list)
    criado_em: datetime
    atualizado_em: datetime
    ultimo_login_em: datetime | None = None


class AuthMeResponse(BaseModel):
    usuario: AuthUserResponse


class AuthUsersListResponse(BaseModel):
    usuarios: list[AuthUserResponse]
    total: int


class AuthMessageResponse(BaseModel):
    status: str
    mensagem: str
    usuario: AuthUserResponse | None = None


AuthTokenResponse.model_rebuild()
