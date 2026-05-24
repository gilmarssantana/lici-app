from __future__ import annotations

from fastapi import APIRouter

from app.schemas.strategic_flow import (
    MemoryConsultRequest,
    MemoryConsultResponse,
    StrategicAnalysisPreparation,
    StrategicAnalysisRequest,
    SuggestedMemoryRegistration,
)
from app.services.memory_core_client import MemoryCoreClient

router = APIRouter(prefix="/fluxo", tags=["LICI Strategic Flow"])
client = MemoryCoreClient()

INTENCOES_VALIDAS = [
    "edital",
    "impugnação",
    "recurso",
    "concorrente",
    "habilitação",
    "contrato",
    "pagamento",
    "órgão",
    "tese",
    "oportunidade",
]

PROTOCOLO_ANALISE_VIVA = [
    "1. Identificar a intenção da pergunta: edital, impugnação, recurso, concorrente, habilitação, contrato, pagamento, órgão, tese ou oportunidade.",
    "2. Consultar memória viva antes da resposta via POST /fluxo/memoria/consultar.",
    "3. Consultar base/RAG quando houver necessidade técnica, jurídica ou documental.",
    "4. Produzir resposta estratégica com diagnóstico, oportunidade, riscos, ataque lícito a concorrentes, blindagem e decisão.",
    "5. Ao final, avaliar se existe aprendizado novo.",
    "6. Se houver aprendizado novo, entregar o bloco MEMÓRIA SUGERIDA.",
    "7. Se o usuário aprovar, registrar em POST /fluxo/memoria/registrar-sugerida.",
]

REGRA_RESPOSTA = [
    "Toda análise licitatória deve seguir o Protocolo Oficial de Análise Viva.",
    "Consultar memória viva antes de análise estratégica sobre edital, impugnação, recurso, órgão, concorrente, habilitação, contrato, pagamento, tese ou oportunidade.",
    "Usar a memória encontrada para identificar padrões, riscos, oportunidade competitiva e defesa do usuário.",
    "Consultar base/RAG quando houver necessidade técnica, jurídica ou documental.",
    "Quando houver aprendizado novo, encerrar a análise com MEMÓRIA SUGERIDA no formato obrigatório.",
    "Só registrar memória sugerida depois de aprovação do usuário.",
]

MEMORIA_SUGERIDA_TEMPLATE = {
    "tipo": "orgao | concorrente | tese | vitoria | perda | risco | padrao | contrato",
    "titulo": "",
    "descricao": "",
    "estrategia": "",
    "aprendizado": "",
    "uso_futuro": "",
    "tags": [],
}

RAG_ORIENTACAO = (
    "Consultar base/RAG quando a pergunta depender de documento, edital, cláusula, jurisprudência, "
    "fundamento legal específico, comparação técnica ou prova documental. Se a pergunta for apenas "
    "operacional/estratégica e a memória for suficiente, a consulta ao RAG pode ser dispensada."
)


@router.get("/protocolo/analise-viva")
def obter_protocolo_analise_viva() -> dict[str, object]:
    return {
        "nome": "Protocolo Oficial de Análise Viva",
        "intencoes_validas": INTENCOES_VALIDAS,
        "protocolo": PROTOCOLO_ANALISE_VIVA,
        "memoria_sugerida_template": MEMORIA_SUGERIDA_TEMPLATE,
        "registro_apenas_com_aprovacao_usuario": True,
    }


@router.post("/memoria/consultar", response_model=MemoryConsultResponse)
def consultar_memoria(payload: MemoryConsultRequest) -> MemoryConsultResponse:
    memoria = client.buscar(payload.termo)
    return MemoryConsultResponse(termo=payload.termo, memoria=memoria)


@router.post("/analise/preparar", response_model=StrategicAnalysisPreparation)
def preparar_analise(payload: StrategicAnalysisRequest) -> StrategicAnalysisPreparation:
    intencao = _identificar_intencao(payload.pergunta)
    termo = payload.termo_memoria or _extrair_termo_memoria(payload.pergunta, intencao)
    memoria = _buscar_memoria_com_fallback(termo)
    consultar_rag = payload.consultar_rag or _deve_consultar_rag(payload.pergunta, intencao)
    return StrategicAnalysisPreparation(
        pergunta=payload.pergunta,
        intencao=intencao,
        termo_memoria=termo,
        memoria_consultada=memoria,
        consultar_rag=consultar_rag,
        rag_orientacao=RAG_ORIENTACAO,
        protocolo=PROTOCOLO_ANALISE_VIVA,
        regra_resposta=REGRA_RESPOSTA,
        memoria_sugerida_template=MEMORIA_SUGERIDA_TEMPLATE,
    )


@router.post("/memoria/registrar-sugerida")
def registrar_memoria_sugerida(payload: SuggestedMemoryRegistration) -> dict:
    return client.registrar(payload.memoria)


def _buscar_memoria_com_fallback(termo: str) -> dict:
    memoria = client.buscar(termo)
    if memoria.get("total", 0) or " " not in termo:
        return memoria

    resultados_por_id: dict[str, dict] = {}
    for parte in termo.split():
        parcial = client.buscar(parte)
        for item in parcial.get("resultados", []):
            item_id = item.get("id") or repr(item)
            resultados_por_id[item_id] = item

    if not resultados_por_id:
        return memoria

    return {
        "total": len(resultados_por_id),
        "resultados": list(resultados_por_id.values()),
        "fallback": "busca por termos individuais",
        "termo_original": termo,
    }


def _identificar_intencao(pergunta: str) -> str:
    texto = pergunta.casefold()
    pesos = {
        "impugnação": ["impugna", "impugnar", "impugnação", "impugnacao"],
        "recurso": ["recurso", "contrarraz", "intenção de recurso", "intencao de recurso", "diligência", "diligencia"],
        "concorrente": ["concorrente", "licitante", "empresa adversária", "adversária", "desclassificar", "inabilitar"],
        "habilitação": ["habilitação", "habilitacao", "sicaf", "certidão", "certidao", "atestado", "cat", "art", "rrt", "balanço", "balanco"],
        "contrato": ["contrato", "execução", "execucao", "fiscalização", "fiscalizacao", "sanção", "sancao", "penalidade"],
        "pagamento": ["pagamento", "nota fiscal", "empenho", "liquidação", "liquidacao", "glosa", "medição", "medicao"],
        "órgão": ["órgão", "orgao", "prefeitura", "município", "municipio", "estado", "secretaria", "autarquia"],
        "tese": ["tese", "fundamento", "jurisprudência", "jurisprudencia", "tcu", "lei 14.133", "lei 13.303"],
        "oportunidade": ["oportunidade", "pncp", "radar", "prospect", "vale a pena", "go/no-go", "go no go"],
        "edital": ["edital", "termo de referência", "termo de referencia", "tr", "etp", "dfd", "cláusula", "clausula"],
    }
    for intencao, termos in pesos.items():
        if any(termo in texto for termo in termos):
            return intencao
    return "oportunidade"


def _extrair_termo_memoria(pergunta: str, intencao: str | None = None) -> str:
    """Heurística operacional inicial.

    Prioriza termos estratégicos recorrentes para aumentar chance de recuperar
    memória útil mesmo quando a análise ainda não informou `termo_memoria`.
    """
    texto = " ".join(pergunta.split())
    texto_norm = texto.casefold()

    termos_prioritarios = [
        "atestado",
        "qualificação técnica",
        "qualificacao tecnica",
        "cat",
        "art",
        "rrt",
        "impugnação",
        "impugnacao",
        "recurso",
        "concorrente",
        "inexequibilidade",
        "amostra",
        "balanço",
        "balanco",
        "sicaf",
        "pagamento",
        "nota fiscal",
        "empenho",
        "reequilíbrio",
        "reequilibrio",
        "glosa",
        "penalidade",
        "contrato",
        "órgão",
        "orgao",
        "edital",
        "tese",
        "oportunidade",
        "pncp",
    ]

    encontrados = [termo for termo in termos_prioritarios if termo in texto_norm]
    if encontrados:
        return " ".join(encontrados[:3])

    if intencao:
        return intencao

    if len(texto) <= 120:
        return texto
    return texto[:120]


def _deve_consultar_rag(pergunta: str, intencao: str) -> bool:
    texto = pergunta.casefold()
    gatilhos = [
        "edital",
        "cláusula",
        "clausula",
        "anexo",
        "termo de referência",
        "termo de referencia",
        "tr",
        "etp",
        "lei",
        "artigo",
        "jurisprudência",
        "jurisprudencia",
        "tcu",
        "documento",
        "pdf",
        "exigência",
        "exigencia",
    ]
    return intencao in {"edital", "impugnação", "recurso", "tese", "habilitação", "contrato"} or any(
        gatilho in texto for gatilho in gatilhos
    )
