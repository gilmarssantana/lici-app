from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from app.schemas.memory import MemoryCreate
from app.schemas.profile import (
    CurrentProfileResponse,
    CurrentProfileState,
    ProfileConfigurationsResponse,
    ProfileSelectRequest,
)
from app.services.audit_log import audit_event
from app.services.memory_core_client import MemoryCoreClient
from app.services.profile_store import JsonOperationalProfileStore


class LiciOperationalProfileEngine:
    def __init__(self, store: JsonOperationalProfileStore | None = None, memory: MemoryCoreClient | None = None):
        self.store = store or JsonOperationalProfileStore()
        self.memory = memory or MemoryCoreClient()

    def info(self) -> dict[str, object]:
        return {
            "nome": "LICI Operational Profile Engine",
            "objetivo": "Permitir que a LICI opere com perfis diferentes sem quebrar funcionalidades existentes.",
            "perfil_padrao": "fornecedor",
            "perfis": ["fornecedor", "consultor", "comprador"],
            "endpoints": [
                "GET /perfil/engine",
                "GET /perfil/atual",
                "POST /perfil/selecionar",
                "GET /perfil/configuracoes",
            ],
            "persistencia": [
                "/root/lici-app/perfis/perfil_atual.json",
                "/root/lici-app/perfis/configuracoes.json",
            ],
            "integracoes": ["Dashboard", "Case Engine", "Memory Core", "Audit Log"],
            "compatibilidade": "O perfil fornecedor mantém os menus e módulos atuais; consultor e comprador nascem estruturais.",
        }

    def atual(self) -> CurrentProfileResponse:
        state = self.store.current()
        config = self.store.get_config(state.perfil_atual)
        if config is None:
            state = CurrentProfileState(perfil_atual="fornecedor", origem="fallback")
            self.store.set_current(state)
            config = self.store.get_config("fornecedor")
        if config is None:
            raise HTTPException(status_code=500, detail="configuração do perfil fornecedor ausente")
        return CurrentProfileResponse(perfil_atual=state.perfil_atual, atualizado_em=state.atualizado_em, configuracao=config)

    def configuracoes(self) -> ProfileConfigurationsResponse:
        configs = self.store.configurations()
        current = self.store.current()
        return ProfileConfigurationsResponse(perfil_atual=current.perfil_atual, total=len(configs), perfis=configs)

    def selecionar(self, payload: ProfileSelectRequest) -> CurrentProfileResponse:
        config = self.store.get_config(payload.perfil)
        if config is None:
            raise HTTPException(status_code=404, detail="perfil operacional não encontrado")
        state = CurrentProfileState(perfil_atual=payload.perfil, atualizado_em=self._now(), origem="selecionado")
        self.store.set_current(state)
        audit_event(
            modulo="profile_engine",
            acao="selecionar_perfil",
            status="ok",
            detalhes={"perfil": payload.perfil, "motivo": payload.motivo, "menus": [item.id for item in config.menus if item.enabled]},
            id_relacionado=payload.perfil,
        )
        self._registrar_memoria_selecao(config.id, config.nome, payload.motivo)
        return CurrentProfileResponse(perfil_atual=state.perfil_atual, atualizado_em=state.atualizado_em, configuracao=config)

    def _registrar_memoria_selecao(self, profile_id: str, nome: str, motivo: str) -> None:
        self.memory.registrar(MemoryCreate(
            tipo="padrao",
            titulo=f"Perfil operacional selecionado: {nome}",
            descricao=f"A LICI passou a operar no perfil {profile_id}.",
            contexto=motivo or "Seleção de perfil operacional.",
            estrategia="Ajustar dashboard, menus, linguagem, prioridades, fluxos, casos, alertas, memórias e documentos ao perfil selecionado.",
            aprendizado="Perfis operacionais permitem reutilizar a mesma LICI para fornecedor, consultor e comprador público sem quebrar módulos existentes.",
            uso_futuro="Consultar perfil atual antes de montar experiência, linguagem e módulos habilitados.",
            tags=["profile-engine", profile_id, "perfil-operacional"],
            fonte="profile_engine",
            confianca=0.8,
        ))

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
