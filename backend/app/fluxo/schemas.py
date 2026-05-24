from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class FluxoAnaliseRequest(BaseModel):
    tipo: Optional[str] = None
    texto: str
    cliente: Optional[str] = None
    orgao: Optional[str] = None
    caso_id: Optional[str] = None


class MemoriaSugerida(BaseModel):
    tipo: Optional[str] = None
    titulo: Optional[str] = None
    conteudo: Optional[str] = None
    contexto: Optional[str] = None
    tags: List[str] = []


class FluxoAnaliseResponse(BaseModel):
    intencao: str
    diagnostico: str
    memorias_consultadas: List[Dict[str, Any]] = []
    riscos: List[str] = []
    oportunidades: List[str] = []
    decisao: str
    score: int
    acao_imediata: str
    caso_id: Optional[str] = None
    prompt_base: Optional[str] = None
    memoria_sugerida: Optional[MemoriaSugerida] = None


class MemoriaConsultaRequest(BaseModel):
    termo: str


class MemoriaRegistroSugeridaRequest(BaseModel):
    memoria: MemoriaSugerida
    aprovado: bool = False
