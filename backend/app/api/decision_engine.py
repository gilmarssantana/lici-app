from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, status

from app.api import security
from app.schemas.decision import DecisionRequest, DecisionResponse
from app.services.audit_log import audit_event
from app.services.case_engine import LiciCaseEngine
from app.services.decision_engine import LiciDecisionEngine

router = APIRouter(prefix="/decisao", tags=["LICI Decision Engine"])
engine = LiciDecisionEngine()
case_engine = LiciCaseEngine()

DECISOES = ["PARTICIPAR", "IMPUGNAR", "ESTRATÉGIA HÍBRIDA", "DESISTIR", "ANALISAR MAIS"]
CRITERIOS_OBRIGATORIOS = [
    "aderência técnica",
    "risco de habilitação",
    "risco jurídico",
    "oportunidade competitiva",
    "risco de execução",
    "histórico/memória viva",
    "necessidade de impugnação",
    "chance estratégica de vitória",
]


@router.get("/engine")
def obter_decision_engine() -> dict[str, object]:
    return {
        "nome": "LICI Decision Engine",
        "objetivo": "Transformar toda análise licitatória em decisão operacional clara.",
        "decisoes": DECISOES,
        "criterios_obrigatorios": CRITERIOS_OBRIGATORIOS,
        "integracoes": ["Protocolo Oficial de Análise Viva", "Memory Core", "Base/RAG quando necessário", "Concorrentes Engine"],
    }


@router.post("/decidir", response_model=DecisionResponse)
def decidir(
    payload: DecisionRequest,
    authorization: str | None = Header(default=None),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
) -> DecisionResponse:
    response = engine.decidir(payload)
    if not payload.registrar_consequencia:
        return response

    user = _authenticated_user_for_consequence(authorization, x_organization_id)
    organization_id = user.get("active_organization_id") or user.get("organization_id")
    response.consequencia_operacional = case_engine.register_decision_consequence(
        payload,
        response,
        organization_id=organization_id,
    )
    return response


def _authenticated_user_for_consequence(
    authorization: str | None,
    x_organization_id: str | None,
) -> dict[str, Any]:
    if not isinstance(authorization, str) or not authorization.lower().startswith("bearer "):
        audit_event("security", "acesso_negado", "erro", {"motivo": "token_ausente", "acao": "registrar_consequencia_decisao"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token obrigatório")

    token = authorization.split(" ", 1)[1].strip()
    user = security.engine.user_from_token(token)
    user = security.org_store.ensure_user_membership(user)
    if not isinstance(x_organization_id, str):
        x_organization_id = None
    if x_organization_id:
        security.org_store.assert_access(user, x_organization_id, action="registrar_consequencia_decisao")
        user["organization_id"] = x_organization_id
        user["active_organization_id"] = x_organization_id
        user["organization_role"] = security.org_store.role_for_user(user, x_organization_id)

    if not security.has_permission(user, "casos:escrever"):
        audit_event(
            "security",
            "acesso_negado",
            "erro",
            {
                "motivo": "permissao_insuficiente",
                "acao": "registrar_consequencia_decisao",
                "usuario": user.get("usuario"),
                "perfil": user.get("perfil"),
                "necessarias": ["casos:escrever"],
                "permissoes_usuario": user.get("permissoes", []),
            },
            user.get("id"),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente")

    return user
