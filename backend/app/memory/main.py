from __future__ import annotations

import time

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
import json

app = FastAPI(title="LICI Memory Core")

try:
    from app.services.observability import ensure_log_dir, structured_log
    ensure_log_dir()
except Exception:  # pragma: no cover
    structured_log = None


@app.middleware("http")
async def memory_observability_middleware(request: Request, call_next):
    started = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        if structured_log:
            structured_log("memory_core", "http_request_exception", "erro", {"method": request.method, "path": request.url.path, "erro": str(exc)})
        raise
    finally:
        if structured_log:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            status = "erro" if status_code >= 500 else ("alerta" if status_code >= 400 else "ok")
            structured_log(
                "memory_core",
                "http_request",
                status,
                {"method": request.method, "path": request.url.path, "status_code": status_code, "duration_ms": duration_ms},
            )

BASE_DIR = Path("/root/lici-app/memoria_viva")
AUDIT_LOG = Path("/root/lici-app/audit/audit.log")

TIPOS_VALIDOS = [
    "orgao",
    "concorrente",
    "tese",
    "vitoria",
    "perda",
    "risco",
    "padrao",
    "contrato",
]

TIPO_PASTA = {
    "orgao": "orgaos",
    "concorrente": "concorrentes",
    "tese": "teses",
    "vitoria": "vitorias",
    "perda": "perdas",
    "risco": "riscos",
    "padrao": "padroes",
    "contrato": "contratos",
}


class Memoria(BaseModel):
    tipo: str
    titulo: str = Field(..., min_length=3)
    descricao: str = Field(..., min_length=3)
    contexto: Optional[str] = ""
    estrategia: Optional[str] = ""
    resultado: Optional[str] = ""
    aprendizado: Optional[str] = ""
    uso_futuro: Optional[str] = ""
    tags: list[str] = Field(default_factory=list)
    fonte: Optional[str] = ""
    confianca: Optional[int] = Field(default=0, ge=0, le=100)


@app.get("/")
def home() -> dict[str, str]:
    return {"status": "LICI Memory Core online"}


@app.post("/memoria/registrar")
def registrar_memoria(memoria: Memoria) -> dict[str, str]:
    if memoria.tipo not in TIPOS_VALIDOS:
        _audit_event(
            modulo="memory_core",
            acao="registro_memoria",
            status="erro",
            detalhes={"erro": "tipo inválido", "tipo": memoria.tipo, "titulo": memoria.titulo},
        )
        return {"erro": "tipo inválido"}

    memoria_id = str(uuid4())
    registro = {
        "id": memoria_id,
        "data": datetime.now(timezone.utc).isoformat(),
        "tipo": memoria.tipo,
        "titulo": memoria.titulo,
        "descricao": memoria.descricao,
        "contexto": memoria.contexto or "",
        "estrategia": memoria.estrategia or "",
        "resultado": memoria.resultado or "",
        "aprendizado": memoria.aprendizado or "",
        "uso_futuro": memoria.uso_futuro or "",
        "tags": memoria.tags,
        "fonte": memoria.fonte or "",
        "confianca": memoria.confianca or 0,
    }

    pasta = BASE_DIR / TIPO_PASTA[memoria.tipo]
    pasta.mkdir(parents=True, exist_ok=True)

    caminho = pasta / f"{memoria_id}.json"
    caminho.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _append_index(registro)

    _audit_event(
        modulo="memory_core",
        acao="registro_memoria",
        status="ok",
        detalhes={"tipo": memoria.tipo, "titulo": memoria.titulo, "arquivo": str(caminho)},
        id_relacionado=memoria_id,
    )

    return {
        "status": "memória registrada",
        "arquivo": str(caminho),
        "id": memoria_id,
    }


@app.get("/memoria/listar/{tipo}")
def listar_memorias(tipo: str) -> list[dict]:
    pasta = _resolver_pasta_tipo(tipo)
    if not pasta.exists():
        return []

    resultados = []
    for arquivo in sorted(pasta.glob("*.json")):
        resultados.append(json.loads(arquivo.read_text(encoding="utf-8")))

    return resultados


@app.get("/memoria/buscar")
def buscar_memoria(q: str) -> dict[str, object]:
    encontrados = []
    termo = q.casefold().strip()

    for arquivo in BASE_DIR.rglob("*.json"):
        if arquivo.name == "memorias.json":
            continue
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        texto = json.dumps(dados, ensure_ascii=False).casefold()
        if termo in texto:
            encontrados.append(dados)

    return {"total": len(encontrados), "resultados": encontrados}


def _resolver_pasta_tipo(tipo: str) -> Path:
    """Aceita tanto o tipo canônico (tese) quanto a pasta plural (teses)."""
    if tipo in TIPO_PASTA:
        return BASE_DIR / TIPO_PASTA[tipo]
    return BASE_DIR / tipo


def _audit_event(modulo: str, acao: str, status: str, detalhes: dict | None = None, id_relacionado: str | None = None) -> None:
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "modulo": modulo,
            "acao": acao,
            "status": status,
            "detalhes": detalhes or {},
            "id_relacionado": id_relacionado,
        }
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _append_index(registro: dict) -> None:
    """Mantém um índice JSON simples para facilitar migração futura."""
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    db_path = BASE_DIR / "memorias.json"
    if db_path.exists():
        try:
            items = json.loads(db_path.read_text(encoding="utf-8"))
            if not isinstance(items, list):
                items = []
        except json.JSONDecodeError:
            items = []
    else:
        items = []

    items.append(registro)
    with NamedTemporaryFile("w", encoding="utf-8", dir=BASE_DIR, delete=False) as tmp:
        json.dump(items, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(db_path)
