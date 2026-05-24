import requests
from typing import Dict, Any, List, Optional
from .prompts import PROMPT_ANALISE_VIVA

MEMORY_CORE_URL = "http://127.0.0.1:8010"


def identificar_intencao(texto: str, tipo: Optional[str] = None) -> str:
    if tipo:
        return tipo.lower()

    t = texto.lower()

    mapa = {
        "impugna": "impugnacao",
        "recurso": "recurso",
        "habilita": "habilitacao",
        "atestado": "habilitacao",
        "contrato": "contrato",
        "execução": "contrato",
        "execucao": "contrato",
        "pagamento": "pagamento",
        "medição": "pagamento",
        "medicao": "pagamento",
        "concorrente": "concorrente",
        "edital": "edital",
        "pregão": "edital",
        "pregao": "edital",
        "órgão": "orgao",
        "orgao": "orgao",
        "tese": "tese",
    }

    for chave, intencao in mapa.items():
        if chave in t:
            return intencao

    return "oportunidade"


def consultar_memoria(termo: str) -> List[Dict[str, Any]]:
    try:
        r = requests.get(
            f"{MEMORY_CORE_URL}/memoria/buscar",
            params={"q": termo},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                return data.get("resultados", [])
    except Exception:
        return []

    return []


def analisar_regras(intencao: str, texto: str) -> Dict[str, Any]:
    t = texto.lower()
    riscos = []
    oportunidades = []

    if "atestado" in t:
        riscos.append("Risco de inabilitação por atestado incompatível, insuficiente ou sem aderência ao objeto.")
        oportunidades.append("Explorar a exigência técnica contra concorrentes sem comprovação equivalente.")

    if "prazo" in t:
        riscos.append("Risco de prazo inexequível ou obrigação operacional excessiva.")
        oportunidades.append("Usar pedido de esclarecimento/impugnação se o prazo limitar competitividade.")

    if "marca" in t or "modelo" in t:
        riscos.append("Risco de direcionamento por marca/modelo ou especificação restritiva.")
        oportunidades.append("Se o usuário atende, transformar especificação restritiva em vantagem competitiva.")

    if "certidão" in t or "certidao" in t:
        riscos.append("Risco documental por certidão vencida, divergente ou ausente.")
        oportunidades.append("Blindar habilitação e monitorar falhas documentais dos concorrentes.")

    if not riscos:
        riscos.append("Risco depende da análise integral do edital, anexos e documentos de habilitação.")

    if not oportunidades:
        oportunidades.append("Mapear requisitos técnicos para converter aderência documental em vantagem competitiva.")

    diagnostico = (
        f"Intenção identificada: {intencao}. "
        "A prioridade é avaliar vantagem competitiva, risco de habilitação, necessidade de impugnação "
        "e uso estratégico lícito do edital."
    )

    return {
        "diagnostico": diagnostico,
        "riscos": riscos,
        "oportunidades": oportunidades,
    }


def decidir(intencao: str, riscos: List[str], oportunidades: List[str]) -> Dict[str, Any]:
    if intencao == "impugnacao":
        return {
            "decisao": "IMPUGNAR",
            "score": 74,
            "acao_imediata": "Redigir impugnação com tese principal, argumento técnico e pedido objetivo de correção.",
        }

    if intencao == "edital":
        return {
            "decisao": "ESTRATÉGIA HÍBRIDA",
            "score": 82,
            "acao_imediata": "Confirmar aderência do usuário às cláusulas críticas antes de decidir entre explorar ou impugnar.",
        }

    if intencao == "habilitacao":
        return {
            "decisao": "PARTICIPAR",
            "score": 80,
            "acao_imediata": "Montar checklist de habilitação e revisar atestados, certidões, registros e vínculos técnicos.",
        }

    if intencao == "concorrente":
        return {
            "decisao": "ESTRATÉGIA HÍBRIDA",
            "score": 77,
            "acao_imediata": "Mapear falhas objetivas do concorrente para manifestação de intenção de recurso ou recurso.",
        }

    return {
        "decisao": "ANALISAR MAIS",
        "score": 62,
        "acao_imediata": "Coletar edital, termo de referência, anexos e documentos críticos para decisão final.",
    }


def sugerir_memoria(intencao: str, texto: str, orgao: Optional[str]) -> Optional[Dict[str, Any]]:
    if len(texto.strip()) < 80 and not orgao:
        return None

    return {
        "tipo": "padrao",
        "titulo": f"Padrão identificado em análise de {intencao}",
        "conteudo": texto[:1200],
        "contexto": f"Órgão: {orgao or 'não informado'}",
        "tags": [intencao, "analise_viva", "orchestrator"],
    }


def executar_fluxo(payload) -> Dict[str, Any]:
    intencao = identificar_intencao(payload.texto, payload.tipo)
    termo_memoria = payload.orgao or payload.cliente or intencao

    memorias = consultar_memoria(termo_memoria)
    analise = analisar_regras(intencao, payload.texto)
    decisao = decidir(intencao, analise["riscos"], analise["oportunidades"])
    memoria_sugerida = sugerir_memoria(intencao, payload.texto, payload.orgao)

    return {
        "intencao": intencao,
        "diagnostico": analise["diagnostico"],
        "memorias_consultadas": memorias,
        "riscos": analise["riscos"],
        "oportunidades": analise["oportunidades"],
        "decisao": decisao["decisao"],
        "score": decisao["score"],
        "acao_imediata": decisao["acao_imediata"],
        "caso_id": payload.caso_id,
        "prompt_base": PROMPT_ANALISE_VIVA,
        "memoria_sugerida": memoria_sugerida,
    }
