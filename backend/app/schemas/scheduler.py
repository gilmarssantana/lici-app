from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.schemas.radar import RadarOpportunity, RadarSearchRequest


class SchedulerConfig(BaseModel):
    uf: str = Field(default="SE", min_length=2, max_length=2)
    dias_busca: int = Field(default=3, ge=1, le=90)
    palavras_chave: list[str] = Field(
        default_factory=lambda: [
            "software",
            "sistema",
            "consultoria",
            "engenharia",
            "manutenção",
            "serviços",
            "tecnologia",
        ]
    )
    limite: int = Field(default=50, ge=1, le=100)
    cliente_padrao: str = "prospect-radar"
    ativo: bool = True
    preparado_para: list[str] = Field(default_factory=lambda: ["systemd timer", "cron"])


class SchedulerRunRequest(BaseModel):
    sobrescrever_config: SchedulerConfig | None = None
    salvar_config: bool = False
    limite: int | None = Field(default=None, ge=1, le=100)


class SchedulerRunLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    iniciado_em: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finalizado_em: str = ""
    status: str = "em_execucao"
    config_usada: SchedulerConfig
    radar_payload: dict[str, Any]
    total_encontradas: int = 0
    novas_oportunidades: int = 0
    duplicadas_evitas: int = 0
    fila_triagem_total: int = 0
    fila_triagem: list[dict[str, Any]] = Field(default_factory=list)
    aviso: str = ""
    erro: str = ""


class SchedulerRunResponse(BaseModel):
    log: SchedulerRunLog
    oportunidades: list[RadarOpportunity]


class SchedulerStatusResponse(BaseModel):
    nome: str = "LICI Scheduler"
    objetivo: str = "Automatizar o Radar para buscar oportunidades e alimentar fila de triagem."
    config: SchedulerConfig
    total_oportunidades_salvas: int
    fila_triagem_total: int
    fila_triagem: list[dict[str, Any]]
    ultimo_log: SchedulerRunLog | None = None
    endpoints: list[str] = Field(
        default_factory=lambda: [
            "GET /scheduler/status",
            "POST /scheduler/executar-radar",
            "GET /scheduler/logs",
        ]
    )
    integracoes: list[str] = Field(default_factory=lambda: ["Radar Engine", "Case Engine", "Memory Core"])
    proxima_execucao_externa: str = "Pronto para ser chamado por systemd timer ou cron via POST /scheduler/executar-radar."


class SchedulerLogsResponse(BaseModel):
    total: int
    logs: list[SchedulerRunLog]
