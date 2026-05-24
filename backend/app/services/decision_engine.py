from __future__ import annotations

from app.api.strategic_flow import (
    PROTOCOLO_ANALISE_VIVA,
    RAG_ORIENTACAO,
    _buscar_memoria_com_fallback,
    _deve_consultar_rag,
    _extrair_termo_memoria,
    _identificar_intencao,
)
from app.schemas.decision import DecisionCriteria, DecisionRequest, DecisionResponse, MemorySuggestion
from app.services.audit_log import audit_event
from app.services.concorrente_store import HybridConcorrenteStore
from app.services.observability import structured_log
from app.services.rag_client import RagClient


class LiciDecisionEngine:
    """Motor de decisão operacional da LICI.

    O objetivo é apoiar a decisão humana com critérios claros, auditáveis e
    consistentes com o Protocolo Oficial de Análise Viva.
    """

    def __init__(self, rag_client: RagClient | None = None, concorrente_store: HybridConcorrenteStore | None = None):
        self.rag_client = rag_client or RagClient()
        self.concorrente_store = concorrente_store or HybridConcorrenteStore()

    def decidir(self, payload: DecisionRequest) -> DecisionResponse:
        intencao = _identificar_intencao(payload.pergunta)
        termo = payload.termo_memoria or _extrair_termo_memoria(payload.pergunta, intencao)
        memoria = _buscar_memoria_com_fallback(termo)
        consultar_rag = payload.consultar_rag or _deve_consultar_rag(payload.pergunta, intencao)
        rag_resultado = self.rag_client.consultar(payload.pergunta) if consultar_rag else None

        criterios = self._normalizar_criterios(payload.criterios, payload.pergunta, memoria, rag_resultado)
        analise_concorrencial = self._analisar_concorrentes(payload.pergunta)
        criterios = self._aplicar_concorrencia_criterios(criterios, analise_concorrencial)
        score = self._calcular_score(criterios)
        score = self._ajustar_score_concorrencial(score, analise_concorrencial)
        decisao = self._decidir(criterios, score)
        riscos = self._riscos_criticos(criterios, rag_resultado)
        if analise_concorrencial.get("nivel") in {"alto", "crítico"}:
            riscos.append(analise_concorrencial.get("resumo") or "Risco concorrencial relevante identificado.")

        response = DecisionResponse(
            decisao=decisao,
            score=score,
            justificativa_objetiva=self._justificativa(decisao, score, criterios),
            riscos_criticos=riscos,
            acao_imediata=self._acao_imediata(decisao),
            risco_concorrencial=analise_concorrencial,
            concorrentes_relevantes=analise_concorrencial.get("concorrentes_relevantes", []),
            oportunidade_ataque=analise_concorrencial.get("oportunidade_ataque", ""),
            recomendacao_blindagem=analise_concorrencial.get("recomendacao_blindagem", ""),
            criterios=criterios,
            intencao=intencao,
            termo_memoria=termo,
            memoria_consultada=memoria,
            consultar_rag=consultar_rag,
            rag_orientacao=self._rag_orientacao(rag_resultado),
            memoria_sugerida=self._memoria_sugerida(decisao, score, criterios, intencao, termo),
            protocolo_aplicado=PROTOCOLO_ANALISE_VIVA,
        )
        audit_event(
            modulo="decision_engine",
            acao="geracao_decisao",
            status="ok",
            detalhes={"decisao": decisao, "score": score, "intencao": intencao, "termo_memoria": termo, "risco_concorrencial": analise_concorrencial.get("nivel"), "concorrentes_relevantes": len(analise_concorrencial.get("concorrentes_relevantes", []))},
            id_relacionado=None,
        )
        return response

    def _normalizar_criterios(
        self,
        criterios: DecisionCriteria,
        pergunta: str,
        memoria: dict,
        rag_resultado: dict | None,
    ) -> DecisionCriteria:
        texto = pergunta.casefold()
        total_memorias = int(memoria.get("total") or 0)

        aderencia = criterios.aderencia_tecnica
        if aderencia is None:
            aderencia = 70 if any(t in texto for t in ["atendo", "temos", "possui", "cumpre"]) else 50
            if any(t in texto for t in ["não temos", "nao temos", "não atende", "nao atende", "não possui", "nao possui"]):
                aderencia = 25

        risco_hab = criterios.risco_habilitacao
        if risco_hab is None:
            risco_hab = 70 if any(t in texto for t in ["atestado", "cat", "art", "rrt", "sicaf", "balanço", "balanco", "certidão", "certidao"]) else 45
            if aderencia >= 75:
                risco_hab = min(risco_hab, 40)

        risco_jur = criterios.risco_juridico
        if risco_jur is None:
            risco_jur = 70 if any(t in texto for t in ["ilegal", "restritivo", "direcionamento", "impugna", "tcu", "lei"]) else 40

        oportunidade = criterios.oportunidade_competitiva
        if oportunidade is None:
            oportunidade = 75 if any(t in texto for t in ["restringe", "poucos", "vantagem", "concorrente", "exclusivo"]) else 55
            if aderencia >= 75 and risco_hab <= 45:
                oportunidade = max(oportunidade, 70)

        risco_exec = criterios.risco_execucao
        if risco_exec is None:
            risco_exec = 70 if any(t in texto for t in ["prazo curto", "multa", "penalidade", "garantia", "execução", "execucao", "reequilíbrio", "reequilibrio"]) else 40

        historico = criterios.historico_memoria_viva
        if historico is None:
            historico = min(100, 45 + total_memorias * 10)

        impugnacao = criterios.necessidade_impugnacao
        if impugnacao is None:
            impugnacao = 80 if any(t in texto for t in ["impugnar", "impugnação", "impugnacao", "ilegal", "restritivo", "direcionamento"]) else 30
            if risco_jur >= 70:
                impugnacao = max(impugnacao, 70)

        chance = criterios.chance_estrategica_vitoria
        if chance is None:
            chance = round((aderencia * 0.35) + (oportunidade * 0.3) + ((100 - risco_hab) * 0.2) + (historico * 0.15))
            chance = max(0, min(100, chance))

        if rag_resultado and rag_resultado.get("erro"):
            # Sem documento/base, reduzimos certeza da decisão, mas não travamos.
            historico = max(0, historico - 5)

        return DecisionCriteria(
            aderencia_tecnica=aderencia,
            risco_habilitacao=risco_hab,
            risco_juridico=risco_jur,
            oportunidade_competitiva=oportunidade,
            risco_execucao=risco_exec,
            historico_memoria_viva=historico,
            necessidade_impugnacao=impugnacao,
            chance_estrategica_vitoria=chance,
        )

    def _analisar_concorrentes(self, pergunta: str) -> dict:
        texto = pergunta.casefold()
        try:
            concorrentes = self.concorrente_store.list()
            eventos = self.concorrente_store.events()
        except Exception as exc:
            audit_event("decision_engine", "concorrentes_fallback_indisponivel", "erro", {"erro": str(exc)})
            structured_log("api", "decision_competitors_unavailable", "erro", {"erro": str(exc)})
            return self._analise_concorrencial_vazia("falha ao consultar concorrentes; decisão preservada sem fator concorrencial")

        if not concorrentes:
            return self._analise_concorrencial_vazia("sem concorrentes cadastrados")

        relevantes = []
        eventos_por_concorrente: dict[str, list] = {}
        for event in eventos:
            eventos_por_concorrente.setdefault(event.concorrente_id, []).append(event)

        for concorrente in concorrentes:
            orgao_match = any((orgao or "").casefold() and (orgao or "").casefold() in texto for orgao in concorrente.orgaos_relacionados)
            segmento_match = bool(concorrente.segmento and concorrente.segmento.casefold() in texto)
            nome_match = bool(concorrente.nome and concorrente.nome.casefold() in texto)
            uf_match = bool(concorrente.uf and f" {concorrente.uf.casefold()}" in f" {texto}")
            evento_match = any((event.orgao or "").casefold() and (event.orgao or "").casefold() in texto for event in eventos_por_concorrente.get(concorrente.id, []))
            if not any([orgao_match, segmento_match, nome_match, uf_match, evento_match]):
                continue
            taxa_vitoria = self._taxa_vitoria(concorrente)
            eventos_c = eventos_por_concorrente.get(concorrente.id, [])
            preco_baixo = len([e for e in eventos_c if e.tipo == "preço muito baixo"]) + len(concorrente.padroes_preco)
            agressivo = len([e for e in eventos_c if e.tipo == "comportamento agressivo"])
            documental = len([e for e in eventos_c if e.tipo in {"padrão documental", "inabilitado"}]) + len(concorrente.padroes_documentais) + concorrente.inabilitacoes
            recorrencia_orgao = len(concorrente.orgaos_relacionados) + len([e for e in eventos_c if e.orgao])
            pontos_risco = concorrente.score_risco + (preco_baixo * 8) + (agressivo * 12) + (recorrencia_orgao * 4) + max(0, taxa_vitoria - 50) * 0.4
            pontos_ataque = documental * 12 + concorrente.inabilitacoes * 8
            relevantes.append({
                "id": concorrente.id,
                "nome": concorrente.nome,
                "cnpj": concorrente.cnpj,
                "segmento": concorrente.segmento,
                "uf": concorrente.uf,
                "risco_operacional": concorrente.risco_operacional,
                "score_risco": concorrente.score_risco,
                "frequencia": concorrente.frequencia,
                "taxa_vitoria": taxa_vitoria,
                "preco_baixo": preco_baixo,
                "comportamento_agressivo": agressivo,
                "padrao_documental": documental,
                "recorrencia_orgao": recorrencia_orgao,
                "oportunidade_ataque_score": round(pontos_ataque),
                "risco_concorrencial_score": round(min(100, pontos_risco)),
                "orgaos_relacionados": concorrente.orgaos_relacionados[:5],
            })

        if not relevantes:
            return self._analise_concorrencial_vazia("nenhum concorrente relacionado ao órgão, segmento ou pergunta")

        relevantes.sort(key=lambda item: (item["risco_concorrencial_score"], item["frequencia"], item["taxa_vitoria"]), reverse=True)
        score_risco = round(min(100, sum(item["risco_concorrencial_score"] for item in relevantes[:5]) / min(len(relevantes), 5)))
        score_ataque = round(max(item["oportunidade_ataque_score"] for item in relevantes))
        nivel = "crítico" if score_risco >= 80 else "alto" if score_risco >= 65 else "médio" if score_risco >= 40 else "baixo"
        preco_baixo_total = sum(item["preco_baixo"] for item in relevantes)
        agressividade_total = sum(item["comportamento_agressivo"] for item in relevantes)
        documental_total = sum(item["padrao_documental"] for item in relevantes)
        recorrente_total = sum(1 for item in relevantes if item["recorrencia_orgao"] > 0)
        ataque = ""
        if documental_total:
            ataque = "Explorar documentalmente atestados, certidões, assinatura, objeto divergente, quantitativo insuficiente, CAT/ART/RRT e histórico de inabilitação dos concorrentes relevantes."
        elif preco_baixo_total:
            ataque = "Monitorar inexequibilidade/preço muito baixo e preparar questionamento objetivo da composição de custos se a proposta concorrente destoar do edital."
        else:
            ataque = "Sem oportunidade documental clara ainda; acompanhar documentos da sessão e registrar novos eventos do concorrente."
        blindagem = "Blindar habilitação e proposta antes da sessão: atestados aderentes, quantitativos, validade documental, vínculo técnico, planilha consistente e justificativa de preço exequível."
        resumo = f"Risco concorrencial {nivel}: {len(relevantes)} concorrente(s) relacionado(s), {recorrente_total} recorrente(s) em órgão/segmento, {preco_baixo_total} padrão(ões) de preço baixo, {documental_total} ponto(s) documental(is) explorável(is)."
        result = {
            "nivel": nivel,
            "score": score_risco,
            "score_oportunidade_ataque": min(100, score_ataque),
            "resumo": resumo,
            "concorrentes_relevantes": relevantes[:10],
            "concorrencia_alta": len(relevantes) >= 3 or score_risco >= 65,
            "concorrencia_agressiva": agressividade_total > 0,
            "concorrente_recorrente_orgao": recorrente_total > 0,
            "historico_inabilitacao": documental_total > 0,
            "padrao_preco_baixo": preco_baixo_total > 0,
            "padrao_documental": documental_total > 0,
            "oportunidade_ataque": ataque,
            "recomendacao_blindagem": blindagem,
        }
        audit_event("decision_engine", "consulta_concorrentes_decisao", "ok", {"nivel": nivel, "score": score_risco, "total_relevantes": len(relevantes)})
        structured_log("api", "decision_competitors_context", "ok", {"nivel": nivel, "score": score_risco, "total_relevantes": len(relevantes)})
        return result

    def _analise_concorrencial_vazia(self, motivo: str) -> dict:
        return {
            "nivel": "não identificado",
            "score": 0,
            "score_oportunidade_ataque": 0,
            "resumo": motivo,
            "concorrentes_relevantes": [],
            "concorrencia_alta": False,
            "concorrencia_agressiva": False,
            "concorrente_recorrente_orgao": False,
            "historico_inabilitacao": False,
            "padrao_preco_baixo": False,
            "padrao_documental": False,
            "oportunidade_ataque": "Sem concorrente relacionado cadastrado; manter monitoramento na sessão e registrar eventos novos.",
            "recomendacao_blindagem": "Aplicar checklist padrão de habilitação/proposta e registrar concorrentes identificados durante a sessão.",
        }

    def _aplicar_concorrencia_criterios(self, c: DecisionCriteria, a: dict) -> DecisionCriteria:
        if not a.get("concorrentes_relevantes"):
            return c
        data = c.model_dump()
        risco_score = int(a.get("score") or 0)
        ataque_score = int(a.get("score_oportunidade_ataque") or 0)
        if a.get("concorrencia_alta") or a.get("concorrencia_agressiva") or a.get("padrao_preco_baixo"):
            data["chance_estrategica_vitoria"] = max(0, int(data["chance_estrategica_vitoria"] or 0) - min(18, round(risco_score / 6)))
            data["risco_habilitacao"] = min(100, int(data["risco_habilitacao"] or 0) + (6 if a.get("concorrencia_agressiva") else 3))
        if a.get("historico_inabilitacao") or a.get("padrao_documental"):
            data["oportunidade_competitiva"] = min(100, int(data["oportunidade_competitiva"] or 0) + min(15, round(ataque_score / 8)))
        if a.get("concorrente_recorrente_orgao"):
            data["historico_memoria_viva"] = min(100, int(data["historico_memoria_viva"] or 0) + 5)
        return DecisionCriteria(**data)

    def _ajustar_score_concorrencial(self, score: int, a: dict) -> int:
        if not a.get("concorrentes_relevantes"):
            return score
        ajuste = 0
        if a.get("concorrencia_alta"):
            ajuste -= 5
        if a.get("concorrencia_agressiva"):
            ajuste -= 5
        if a.get("padrao_preco_baixo"):
            ajuste -= 4
        if a.get("historico_inabilitacao") or a.get("padrao_documental"):
            ajuste += 4
        return max(0, min(100, score + ajuste))

    def _taxa_vitoria(self, c) -> float:
        total = c.vitorias + c.derrotas + c.inabilitacoes
        return round((c.vitorias / total) * 100, 2) if total else 0

    def _calcular_score(self, c: DecisionCriteria) -> int:
        assert c.aderencia_tecnica is not None
        assert c.risco_habilitacao is not None
        assert c.risco_juridico is not None
        assert c.oportunidade_competitiva is not None
        assert c.risco_execucao is not None
        assert c.historico_memoria_viva is not None
        assert c.necessidade_impugnacao is not None
        assert c.chance_estrategica_vitoria is not None

        score = (
            c.aderencia_tecnica * 0.22
            + (100 - c.risco_habilitacao) * 0.16
            + (100 - c.risco_juridico) * 0.10
            + c.oportunidade_competitiva * 0.18
            + (100 - c.risco_execucao) * 0.12
            + c.historico_memoria_viva * 0.08
            + (100 - c.necessidade_impugnacao) * 0.04
            + c.chance_estrategica_vitoria * 0.10
        )
        return max(0, min(100, round(score)))

    def _decidir(self, c: DecisionCriteria, score: int) -> str:
        assert c.aderencia_tecnica is not None
        assert c.risco_habilitacao is not None
        assert c.risco_juridico is not None
        assert c.oportunidade_competitiva is not None
        assert c.risco_execucao is not None
        assert c.necessidade_impugnacao is not None
        assert c.chance_estrategica_vitoria is not None

        if c.necessidade_impugnacao >= 75 and c.risco_juridico >= 65:
            return "IMPUGNAR"
        if score < 35 or (c.aderencia_tecnica < 35 and c.chance_estrategica_vitoria < 45) or c.risco_execucao >= 85:
            return "DESISTIR"
        if c.necessidade_impugnacao >= 70 and (c.aderencia_tecnica < 60 or c.risco_juridico >= 75):
            return "IMPUGNAR"
        if c.necessidade_impugnacao >= 60 and c.aderencia_tecnica >= 60 and c.oportunidade_competitiva >= 55:
            return "ESTRATÉGIA HÍBRIDA"
        if score >= 65 and c.aderencia_tecnica >= 60 and c.risco_habilitacao < 70 and c.risco_execucao < 75:
            return "PARTICIPAR"
        return "ANALISAR MAIS"

    def _riscos_criticos(self, c: DecisionCriteria, rag_resultado: dict | None) -> list[str]:
        riscos: list[str] = []
        if (c.aderencia_tecnica or 0) < 60:
            riscos.append("Aderência técnica insuficiente ou não comprovada.")
        if (c.risco_habilitacao or 0) >= 65:
            riscos.append("Risco de inabilitação por documentação, atestado, SICAF, balanço ou qualificação técnica.")
        if (c.risco_juridico or 0) >= 65:
            riscos.append("Risco jurídico relevante no edital/exigência; pode exigir impugnação ou esclarecimento.")
        if (c.risco_execucao or 0) >= 65:
            riscos.append("Risco de execução contratual elevado: prazo, custo, sanção, garantia, medição ou reequilíbrio.")
        if (c.necessidade_impugnacao or 0) >= 70:
            riscos.append("Necessidade alta de impugnação antes de proposta segura.")
        if rag_resultado and rag_resultado.get("erro"):
            riscos.append("Base/RAG não respondeu; validar documento/cláusula antes de decisão final.")
        return riscos or ["Nenhum risco crítico identificado; confirmar com edital/documentos antes da decisão final."]

    def _justificativa(self, decisao: str, score: int, c: DecisionCriteria) -> str:
        return (
            f"Decisão {decisao} com score {score}/100, considerando aderência técnica {c.aderencia_tecnica}, "
            f"risco de habilitação {c.risco_habilitacao}, risco jurídico {c.risco_juridico}, "
            f"oportunidade competitiva {c.oportunidade_competitiva}, risco de execução {c.risco_execucao}, "
            f"histórico/memória viva {c.historico_memoria_viva}, necessidade de impugnação {c.necessidade_impugnacao} "
            f"e chance estratégica de vitória {c.chance_estrategica_vitoria}."
        )

    def _acao_imediata(self, decisao: str) -> str:
        return {
            "PARTICIPAR": "Avançar para checklist de habilitação/proposta e blindar documentos críticos antes da sessão.",
            "IMPUGNAR": "Preparar impugnação objetiva com tese principal, prova técnica e pedido de ajuste/reabertura de prazo se cabível.",
            "ESTRATÉGIA HÍBRIDA": "Protocolar esclarecimento/impugnação seletiva sem abrir mão da preparação para participar se a exigência favorecer o usuário.",
            "DESISTIR": "Não alocar esforço comercial sem mudança relevante no edital, margem, documentação ou risco de execução.",
            "ANALISAR MAIS": "Coletar edital, TR/anexos, requisitos de habilitação, planilha, prazos, margem e documentos próprios antes da decisão final.",
        }[decisao]

    def _rag_orientacao(self, rag_resultado: dict | None) -> str:
        if rag_resultado is None:
            return RAG_ORIENTACAO
        if rag_resultado.get("erro"):
            return f"{RAG_ORIENTACAO} Resultado: consulta pendente/indisponível ({rag_resultado.get('detalhe')})."
        return "Base/RAG consultada; usar os achados documentais para confirmar fundamento, cláusula e risco."

    def _memoria_sugerida(
        self,
        decisao: str,
        score: int,
        c: DecisionCriteria,
        intencao: str,
        termo: str,
    ) -> MemorySuggestion | None:
        if decisao == "ANALISAR MAIS" and score >= 45:
            return None
        return MemorySuggestion(
            tipo="padrao" if decisao in {"PARTICIPAR", "ESTRATÉGIA HÍBRIDA", "ANALISAR MAIS"} else "risco",
            titulo=f"Decision Engine: {decisao} para {intencao}",
            descricao=f"Motor de decisão gerou {decisao} com score {score}/100 para termo '{termo}'.",
            estrategia=self._acao_imediata(decisao),
            aprendizado=(
                "Decisão baseada em aderência técnica, risco de habilitação, risco jurídico, oportunidade competitiva, "
                "risco de execução, memória viva, necessidade de impugnação e chance estratégica de vitória."
            ),
            uso_futuro="Reutilizar como padrão comparativo em análises futuras com critérios semelhantes.",
            tags=["decision-engine", intencao, decisao.lower().replace(" ", "-")],
        )
