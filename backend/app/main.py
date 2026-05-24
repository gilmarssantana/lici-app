from __future__ import annotations
from app.fluxo.router import router as fluxo_router

import time

from fastapi import FastAPI, Request

from app.api.alert_engine import router as alert_engine_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.case_engine import router as case_engine_router
from app.api.chat_engine import router as chat_engine_router
from app.api.consultor_engine import router as consultor_engine_router
from app.api.company_document import router as company_document_router
from app.api.concorrentes_engine import router as concorrentes_engine_router
from app.api.dashboard import router as dashboard_router
from app.api.decision_engine import router as decision_engine_router
from app.api.document_generator import router as document_generator_router
from app.api.edital_analyzer import router as edital_analyzer_router
from app.api.export_engine import router as export_engine_router
from app.api.fornecedor_full import router as fornecedor_full_router
from app.api.consultor_full import router as consultor_full_router
from app.api.global_search import router as global_search_router
from app.api.healthcheck import health_full
from app.api.ia_assistiva import router as ia_assistiva_router
from app.api.memory import router as memory_router
from app.api.observability import observability_status
from app.api.notificacoes import router as notificacoes_router
from app.api.organizations import router as organizations_router
from app.api.orgaos_engine import router as orgaos_engine_router
from app.api.profile_engine import router as profile_engine_router
from app.api.radar_engine import router as radar_engine_router
from app.api.scheduler import router as scheduler_router
from app.api.strategic_flow import router as strategic_flow_router
from app.api.triage_engine import router as triage_engine_router
from app.api.upload_engine import router as upload_engine_router
from app.services.observability import ensure_log_dir, structured_log

app = FastAPI(title="LICI App", version="0.1.0")
ensure_log_dir()

LOCAL_EXPECTED_AUTH_BLOCK_PATHS = {
    "/dashboard/resumo",
    "/radar/engine",
    "/alertas/engine",
    "/casos/engine",
    "/fornecedor-full/engine",
    "/consultor-full/engine",
}


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        structured_log(
            "api",
            "http_request_exception",
            "erro",
            {"method": request.method, "path": request.url.path, "erro": str(exc)},
        )
        raise
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        client_host = request.client.host if request.client else None
        expected_auth_block = (
            status_code == 401
            and client_host in {"127.0.0.1", "::1"}
            and request.url.path in LOCAL_EXPECTED_AUTH_BLOCK_PATHS
        )
        status = "ok" if expected_auth_block else ("erro" if status_code >= 500 else ("alerta" if status_code >= 400 else "ok"))
        structured_log(
            "api",
            "http_request",
            status,
            {
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client": client_host,
                "organization_id": request.headers.get("x-organization-id") or "default-org",
                "expected_auth_block": expected_auth_block,
            },
        )
        if duration_ms >= 2000:
            structured_log("api", "api_slow", "alerta", {"path": request.url.path, "duration_ms": duration_ms, "status_code": status_code})

app.include_router(alert_engine_router)
app.include_router(audit_router)
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(global_search_router)
app.include_router(chat_engine_router)
app.include_router(ia_assistiva_router)
app.include_router(memory_router)
app.include_router(strategic_flow_router)
app.include_router(decision_engine_router)
app.include_router(document_generator_router)
app.include_router(edital_analyzer_router)
app.include_router(export_engine_router)
app.include_router(fornecedor_full_router)
app.include_router(consultor_full_router)
app.include_router(company_document_router)
app.include_router(case_engine_router)
app.include_router(consultor_engine_router)
app.include_router(concorrentes_engine_router)
app.include_router(notificacoes_router)
app.include_router(orgaos_engine_router)
app.include_router(profile_engine_router)
app.include_router(dashboard_router)
app.include_router(radar_engine_router)
app.include_router(scheduler_router)
app.include_router(triage_engine_router)
app.include_router(upload_engine_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "lici-app"}


app.get("/health/full")(health_full)
app.get("/observabilidade/status")(observability_status)

app.include_router(fluxo_router, prefix="/fluxo", tags=["Fluxo Vivo"])

# Fluxo Orchestrator
app.include_router(fluxo_router)
