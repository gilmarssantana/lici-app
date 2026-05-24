from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.security import require_permission
from app.core.config import settings
from app.schemas.memory import MemoryCreate, MemoryRecord, MemorySearchResult, MemoryUpdate
from app.services.audit_log import audit_event
from app.services.memory_store import HybridMemoryStore

router = APIRouter(prefix="/memoria", tags=["LICI Memory Core"])
store = HybridMemoryStore(settings.memory_root)


@router.post("/registrar", response_model=MemoryRecord)
def registrar_memoria(payload: MemoryCreate, user: dict = Depends(require_permission("memoria:escrever"))) -> MemoryRecord:
    record = store.create(payload, organization_id=user.get("active_organization_id") or user.get("organization_id"))
    audit_event(
        modulo="memory",
        acao="registro_memoria",
        status="ok",
        detalhes={"tipo": record.tipo, "titulo": record.titulo},
        id_relacionado=record.id,
    )
    return record


@router.get("/listar", response_model=MemorySearchResult)
def listar_memorias(tipo: str | None = Query(default=None), user: dict = Depends(require_permission("memoria:ler"))) -> MemorySearchResult:
    items = store.list(tipo=tipo, organization_id=user.get("active_organization_id") or user.get("organization_id"))
    return MemorySearchResult(total=len(items), items=items)


@router.get("/listar/{tipo}", response_model=MemorySearchResult)
def listar_memorias_por_tipo(tipo: str, user: dict = Depends(require_permission("memoria:ler"))) -> MemorySearchResult:
    """Alias compatível com o serviço isolado de memória."""
    items = store.list(tipo=tipo, organization_id=user.get("active_organization_id") or user.get("organization_id"))
    return MemorySearchResult(total=len(items), items=items)


@router.get("/buscar", response_model=MemorySearchResult)
def buscar_memorias(
    termo: str = Query(default=""),
    q: str | None = Query(default=None),
    tipo: str | None = Query(default=None),
    user: dict = Depends(require_permission("memoria:ler")),
) -> MemorySearchResult:
    """Busca por memória.

    Mantém o parâmetro atual `termo` e aceita `q` para compatibilidade com
    `GET /memoria/buscar?q=...` do Memory Core oficial.
    """
    termo_busca = q if q is not None else termo
    items = store.search(termo=termo_busca, tipo=tipo, organization_id=user.get("active_organization_id") or user.get("organization_id"))
    return MemorySearchResult(total=len(items), items=items)


@router.get("/{memory_id}", response_model=MemoryRecord)
def obter_memoria(memory_id: str, user: dict = Depends(require_permission("memoria:ler"))) -> MemoryRecord:
    org = user.get("active_organization_id") or user.get("organization_id")
    item = store.get(memory_id, organization_id=org)
    if item:
        return item
    if store.exists(memory_id):
        audit_event("security", "acesso_negado_cross_org", "erro", {"recurso": "memoria", "memory_id": memory_id, "organization_id": org}, memory_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memória pertence a outra organização")
    raise HTTPException(status_code=404, detail="memória não encontrada")


@router.patch("/{memory_id}", response_model=MemoryRecord)
def atualizar_memoria(memory_id: str, payload: MemoryUpdate, user: dict = Depends(require_permission("memoria:escrever"))) -> MemoryRecord:
    org = user.get("active_organization_id") or user.get("organization_id")
    item = obter_memoria(memory_id, user)
    data = item.model_dump()
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            data[key] = value
    record = MemoryRecord(**data)
    saved = store.upsert(record)
    audit_event("memory", "atualizacao_memoria", "ok", {"tipo": saved.tipo, "titulo": saved.titulo}, saved.id)
    return saved


@router.post("/{memory_id}/arquivar", response_model=MemoryRecord)
def arquivar_memoria(memory_id: str, user: dict = Depends(require_permission("memoria:escrever"))) -> MemoryRecord:
    item = obter_memoria(memory_id, user)
    tags = list(item.tags or [])
    if "arquivado" not in tags:
        tags.append("arquivado")
    data = item.model_dump()
    data["tags"] = tags
    data["uso_futuro"] = (data.get("uso_futuro") or "") + f"\n[Arquivado em {datetime.now(timezone.utc).isoformat()}]"
    saved = store.upsert(MemoryRecord(**data))
    audit_event("memory", "arquivamento_memoria", "ok", {"tipo": saved.tipo, "titulo": saved.titulo}, saved.id)
    return saved


