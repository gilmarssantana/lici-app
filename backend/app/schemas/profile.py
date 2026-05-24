from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

OperationalProfileId = Literal["fornecedor", "consultor", "comprador"]


class ProfileMenuItem(BaseModel):
    id: str
    label: str
    icon: str = ""
    enabled: bool = True
    status: str = "ativo"


class OperationalProfileConfig(BaseModel):
    id: OperationalProfileId
    nome: str
    descricao: str
    linguagem_recomendada: str
    prioridades: list[str] = Field(default_factory=list)
    menus: list[ProfileMenuItem] = Field(default_factory=list)
    modulos_habilitados: list[str] = Field(default_factory=list)
    fluxos: list[str] = Field(default_factory=list)
    tipos_caso: list[str] = Field(default_factory=list)
    tipos_alerta: list[str] = Field(default_factory=list)
    tipos_memoria: list[str] = Field(default_factory=list)
    documentos_gerados: list[str] = Field(default_factory=list)
    dashboard: dict = Field(default_factory=dict)


class CurrentProfileState(BaseModel):
    perfil_atual: OperationalProfileId = "fornecedor"
    atualizado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    origem: str = "default"


class ProfileSelectRequest(BaseModel):
    perfil: OperationalProfileId
    motivo: str = ""


class CurrentProfileResponse(BaseModel):
    perfil_atual: OperationalProfileId
    atualizado_em: str
    configuracao: OperationalProfileConfig


class ProfileConfigurationsResponse(BaseModel):
    perfil_atual: OperationalProfileId
    total: int
    perfis: list[OperationalProfileConfig]
