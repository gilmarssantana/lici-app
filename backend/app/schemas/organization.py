from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

OrganizationRole = Literal["admin_global", "admin_org", "operador", "leitura"]
OrganizationStatus = Literal["ativa", "inativa"]


class OrganizationCreateRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=180)
    slug: str | None = Field(default=None, max_length=120)


class OrganizationResponse(BaseModel):
    id: str
    nome: str
    slug: str
    status: OrganizationStatus = "ativa"
    criado_em: datetime
    atualizado_em: datetime
    fallback_single_org: bool | None = None
    role: OrganizationRole | None = None


class OrganizationMembershipRequest(BaseModel):
    user_id: str
    organization_id: str
    role: OrganizationRole = "operador"


class OrganizationMembershipResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    role: OrganizationRole
    status: str
    criado_em: datetime
    atualizado_em: datetime


class OrganizationSwitchRequest(BaseModel):
    organization_id: str


class OrganizationContextResponse(BaseModel):
    active_organization_id: str
    organization_role: OrganizationRole
    organizations: list[OrganizationResponse]
    active_users: list[dict] = Field(default_factory=list)
