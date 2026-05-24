from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.security import require_permission
from app.schemas.chat import ChatConversationsResponse, ChatHistoryResponse, ChatMessageRequest, ChatMessageResponse
from app.schemas.chat_action import ChatActionRequest, ChatActionResponse
from app.services.chat_actions import LiciChatActions
from app.services.chat_engine import LiciChatEngine

router = APIRouter(prefix="/chat", tags=["LICI Chat"])
engine = LiciChatEngine()
actions = LiciChatActions()


@router.get("/engine")
def obter_chat_engine(_: dict = Depends(require_permission("dados:ler"))) -> dict:
    return engine.engine_info()


@router.post("/mensagem", response_model=ChatMessageResponse)
def enviar_mensagem(payload: ChatMessageRequest, user: dict = Depends(require_permission("dados:ler"))) -> ChatMessageResponse:
    return engine.conversar(payload, user)


@router.get("/historico", response_model=ChatHistoryResponse)
def historico_chat(
    conversa_id: str | None = Query(default=None),
    limite: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_permission("dados:ler")),
) -> dict:
    return engine.historico(conversa_id=conversa_id, limite=limite, organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/conversas", response_model=ChatConversationsResponse)
def listar_conversas(user: dict = Depends(require_permission("dados:ler"))) -> dict:
    return engine.conversas(organization_id=user.get("active_organization_id") or user.get("organization_id"))


@router.get("/metricas")
def metricas_chat(_: dict = Depends(require_permission("dados:ler"))) -> dict:
    data = engine.metricas()
    data["acoes"] = actions.metricas_acoes()
    return data


@router.post("/acao", response_model=ChatActionResponse)
def chat_acao(payload: ChatActionRequest, user: dict = Depends(require_permission("dados:ler"))) -> ChatActionResponse:
    return actions.handle(payload, user)
