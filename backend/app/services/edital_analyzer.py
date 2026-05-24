from __future__ import annotations

import re

from app.api.strategic_flow import _buscar_memoria_com_fallback, _extrair_termo_memoria
from app.schemas.decision import DecisionCriteria, DecisionRequest, MemorySuggestion
from app.schemas.edital import (
    EditalAnalysisResponse,
    EditalAnalyzeTextRequest,
    EditalChecklistItem,
    EditalChecklistRequest,
    EditalChecklistResponse,
    EditalResumo,
)
from app.services.decision_engine import LiciDecisionEngine
from app.services.rag_client import RagClient


class LiciEditalAnalyzer:
    """Analisador estruturado de editais para alimentar o Decision Engine."""

    def __init__(self, decision_engine: LiciDecisionEngine | None = None, rag_client: RagClient | None = None):
        self.decision_engine = decision_engine or LiciDecisionEngine()
        self.rag_client = rag_client or RagClient()

    def analisar_texto(self, payload: EditalAnalyzeTextRequest) -> EditalAnalysisResponse:
        texto = self._normalizar(payload.texto)
        termo = payload.termo_memoria or _extrair_termo_memoria(texto, "edital")
        memoria = _buscar_memoria_com_fallback(termo)
        rag = self.rag_client.consultar(texto[:4000]) if payload.consultar_rag else None

        resumo = self._resumo(texto)
        riscos = self._riscos(texto)
        restritivas = self._clausulas_restritivas(texto)
        oportunidades_impugnacao = self._oportunidades_impugnacao(texto, restritivas)
        pontos_ataque = self._pontos_ataque_concorrentes(texto)
        blindagem = self._blindagem_usuario(texto)
        oportunidades = self._oportunidades(texto, restritivas, pontos_ataque)
        checklist = self._checklist(texto, riscos, blindagem, pontos_ataque)

        criterios = self._criterios_para_decision_engine(texto, riscos, restritivas, oportunidades, memoria)
        decision = self.decision_engine.decidir(
            DecisionRequest(
                pergunta=f"Análise de edital: {texto[:3000]}",
                termo_memoria=termo,
                criterios=criterios,
                contexto=payload.contexto_usuario,
                consultar_rag=payload.consultar_rag,
            )
        )

        memoria_sugerida = self._memoria_sugerida(decision.memoria_sugerida, resumo, riscos, oportunidades)

        return EditalAnalysisResponse(
            resumo_edital=resumo,
            riscos=riscos,
            oportunidades=oportunidades,
            clausulas_restritivas=restritivas,
            oportunidades_impugnacao=oportunidades_impugnacao,
            pontos_ataque_concorrentes=pontos_ataque,
            blindagem_usuario=blindagem,
            checklist=checklist,
            decisao_recomendada=decision,
            memoria_consultada=memoria,
            rag_resultado=rag,
            memoria_sugerida=memoria_sugerida,
        )

    def checklist(self, payload: EditalChecklistRequest) -> EditalChecklistResponse:
        texto = self._normalizar(payload.texto)
        termo = payload.termo_memoria or _extrair_termo_memoria(texto, "edital")
        memoria = _buscar_memoria_com_fallback(termo)
        riscos = self._riscos(texto)
        blindagem = self._blindagem_usuario(texto)
        ataques = self._pontos_ataque_concorrentes(texto)
        return EditalChecklistResponse(
            checklist=self._checklist(texto, riscos, blindagem, ataques),
            riscos_de_inabilitacao=riscos,
            blindagem_usuario=blindagem,
            pontos_ataque_concorrentes=ataques,
            memoria_consultada=memoria,
        )

    def _normalizar(self, texto: str) -> str:
        return re.sub(r"\s+", " ", texto).strip()

    def _resumo(self, texto: str) -> EditalResumo:
        return EditalResumo(
            objeto=self._extrair_objeto(texto),
            modalidade=self._extrair_modalidade(texto),
            prazos_criticos=self._extrair_prazos(texto),
            exigencias_habilitacao=self._extrair_exigencias_habilitacao(texto),
            qualificacao_tecnica=self._extrair_qualificacao_tecnica(texto),
            atestados=self._extrair_atestados(texto),
        )

    def _extrair_objeto(self, texto: str) -> str:
        padroes = [
            r"objeto\s*[:\-]\s*(.{20,350}?)(?:\.|;|\n| habilita| modalidade| julgamento)",
            r"contratação\s+de\s+(.{20,300}?)(?:\.|;|\n)",
            r"contratacao\s+de\s+(.{20,300}?)(?:\.|;|\n)",
        ]
        for p in padroes:
            m = re.search(p, texto, flags=re.IGNORECASE)
            if m:
                return m.group(1).strip(" :-")
        return "Objeto não identificado automaticamente; confirmar no item 'Objeto' do edital/TR."

    def _extrair_modalidade(self, texto: str) -> str:
        modalidades = ["pregão eletrônico", "pregao eletronico", "concorrência", "concorrencia", "dispensa", "inexigibilidade", "leilão", "leilao", "diálogo competitivo", "dialogo competitivo"]
        lower = texto.casefold()
        for mod in modalidades:
            if mod in lower:
                return mod.upper()
        return "Modalidade não identificada automaticamente."

    def _extrair_prazos(self, texto: str) -> list[str]:
        achados = []
        for m in re.finditer(r"(?:\d{1,2}/\d{1,2}/\d{2,4}|\d+\s+dias|\d+\s+horas)", texto, flags=re.IGNORECASE):
            trecho = texto[max(0, m.start() - 80) : min(len(texto), m.end() + 80)]
            achados.append(trecho.strip())
        return achados[:10] or ["Prazos críticos não identificados automaticamente; verificar abertura, impugnação, esclarecimentos, entrega e execução."]

    def _extrair_exigencias_habilitacao(self, texto: str) -> list[str]:
        termos = ["habilitação", "habilitacao", "sicaf", "regularidade fiscal", "trabalhista", "certidão", "certidao", "balanço", "balanco", "patrimônio líquido", "patrimonio liquido"]
        return self._sentencas_com_termos(texto, termos, limite=12) or ["Exigências de habilitação não identificadas automaticamente; revisar capítulo de habilitação."]

    def _extrair_qualificacao_tecnica(self, texto: str) -> list[str]:
        termos = ["qualificação técnica", "qualificacao tecnica", "capacidade técnica", "capacidade tecnica", "cat", "art", "rrt", "responsável técnico", "responsavel tecnico", "registro no conselho", "crea", "cau", "crm", "crq"]
        return self._sentencas_com_termos(texto, termos, limite=12) or ["Qualificação técnica não identificada automaticamente; conferir exigências técnicas e conselhos profissionais."]

    def _extrair_atestados(self, texto: str) -> list[str]:
        termos = ["atestado", "atestados", "comprovação de capacidade", "comprovacao de capacidade", "quantitativo", "50%", "100%", "similar", "compatível", "compativel"]
        return self._sentencas_com_termos(texto, termos, limite=12) or ["Atestados não identificados automaticamente; confirmar se há exigência de quantidade, objeto similar, CAT/ART/RRT e emitente."]

    def _riscos(self, texto: str) -> list[str]:
        riscos = []
        lower = texto.casefold()
        if any(t in lower for t in ["atestado", "cat", "art", "rrt"]):
            riscos.append("Risco de inabilitação por atestado/CAT/ART/RRT incompatível, insuficiente ou sem vínculo com o objeto.")
        if any(t in lower for t in ["sicaf", "certidão", "certidao", "regularidade fiscal", "trabalhista"]):
            riscos.append("Risco documental em SICAF/certidões/regularidade fiscal e trabalhista.")
        if any(t in lower for t in ["balanço", "balanco", "índice", "indice", "patrimônio líquido", "patrimonio liquido"]):
            riscos.append("Risco econômico-financeiro por balanço, índices ou patrimônio líquido.")
        if any(t in lower for t in ["amostra", "prova de conceito", "catálogo", "catalogo", "marca", "modelo"]):
            riscos.append("Risco de desclassificação por amostra, catálogo, marca/modelo ou especificação técnica inferior.")
        if any(t in lower for t in ["prazo", "multa", "garantia", "sanção", "sancao", "penalidade"]):
            riscos.append("Risco de execução por prazo, multa, garantia, sanções ou penalidades contratuais.")
        return riscos or ["Riscos específicos não detectados automaticamente; análise humana deve validar habilitação, julgamento e execução."]

    def _clausulas_restritivas(self, texto: str) -> list[str]:
        termos = ["exclusivo", "vedada", "vedado", "somente", "obrigatório", "obrigatorio", "100%", "marca", "fabricante", "certificação", "certificacao", "sede", "distância", "distancia"]
        sentencas = self._sentencas_com_termos(texto, termos, limite=12)
        return sentencas or ["Nenhuma cláusula restritiva detectada automaticamente; verificar se exigências técnicas têm justificativa proporcional."]

    def _oportunidades_impugnacao(self, texto: str, restritivas: list[str]) -> list[str]:
        lower = texto.casefold()
        oportunidades = []
        if any(t in lower for t in ["100%", "integral"]):
            oportunidades.append("Avaliar impugnação contra atestado integral/100% se não houver justificativa técnica proporcional.")
        if any(t in lower for t in ["marca", "fabricante", "exclusivo"]):
            oportunidades.append("Avaliar impugnação por possível direcionamento de marca/fabricante ou restrição indevida.")
        if any(t in lower for t in ["sede", "distância", "distancia", "local"]):
            oportunidades.append("Avaliar impugnação de exigência geográfica/local se não houver justificativa operacional robusta.")
        if restritivas and not oportunidades:
            oportunidades.append("Pedir esclarecimento ou impugnar cláusulas restritivas sem motivação técnica suficiente.")
        return oportunidades

    def _pontos_ataque_concorrentes(self, texto: str) -> list[str]:
        ataques = [
            "Conferir se concorrentes apresentaram atestados com objeto, quantitativo e complexidade compatíveis.",
            "Verificar assinatura, validade, CNPJ/razão social e emitente dos documentos de habilitação.",
        ]
        lower = texto.casefold()
        if any(t in lower for t in ["cat", "art", "rrt"]):
            ataques.append("Atacar concorrente que apresentar CAT/ART/RRT ausente, divergente ou sem vínculo com o responsável técnico exigido.")
        if any(t in lower for t in ["amostra", "catálogo", "catalogo", "marca", "modelo"]):
            ataques.append("Checar se marca/modelo/catálogo do concorrente atende integralmente às especificações; divergência material sustenta desclassificação.")
        if any(t in lower for t in ["inexequível", "inexequivel", "preço", "preco"]):
            ataques.append("Monitorar preço inexequível ou acima do máximo, exigindo diligência/justificativa quando cabível.")
        return ataques

    def _blindagem_usuario(self, texto: str) -> list[str]:
        blindagem = [
            "Montar matriz edital x documento antes da sessão.",
            "Validar certidões, SICAF, assinaturas, poderes de representação e validade documental.",
            "Separar atestados por similaridade, quantitativo, período, emitente e vínculo com o objeto.",
        ]
        lower = texto.casefold()
        if any(t in lower for t in ["cat", "art", "rrt", "responsável técnico", "responsavel tecnico"]):
            blindagem.append("Conferir CAT/ART/RRT, registro em conselho e vínculo do responsável técnico antes de enviar proposta.")
        if any(t in lower for t in ["amostra", "catálogo", "catalogo", "marca", "modelo"]):
            blindagem.append("Preparar catálogo, ficha técnica, marca/modelo e amostra exatamente aderentes ao edital.")
        return blindagem

    def _oportunidades(self, texto: str, restritivas: list[str], ataques: list[str]) -> list[str]:
        oportunidades = []
        lower = texto.casefold()
        if any(t in lower for t in ["atestado", "qualificação técnica", "qualificacao tecnica", "cat", "art"]):
            oportunidades.append("Se o usuário atende às exigências técnicas, usar a barreira como vantagem competitiva contra concorrentes menos preparados.")
        if restritivas:
            oportunidades.append("Transformar cláusulas restritivas em estratégia: explorar se favorecem o usuário; impugnar se impedem participação ou são claramente ilegais.")
        if ataques:
            oportunidades.append("Preparar roteiro de fiscalização dos documentos dos concorrentes para eventual recurso/inabilitação.")
        return oportunidades or ["Oportunidade principal depende de margem, aderência documental e competitividade real do certame."]

    def _checklist(self, texto: str, riscos: list[str], blindagem: list[str], ataques: list[str]) -> list[EditalChecklistItem]:
        itens = [
            EditalChecklistItem(fase="edital", item="Confirmar objeto, modalidade, critério de julgamento e valor estimado", risco="Objeto/critério mal interpretado", acao="Montar ficha-resumo do edital", prioridade="alta"),
            EditalChecklistItem(fase="habilitação", item="Mapear todos os documentos exigidos", risco="Inabilitação por ausência documental", acao="Criar matriz edital x documento", prioridade="alta"),
            EditalChecklistItem(fase="julgamento", item="Validar proposta, marca/modelo, planilha e preço", risco="Desclassificação por desconformidade ou preço", acao="Revisar proposta antes do envio", prioridade="alta"),
            EditalChecklistItem(fase="execução", item="Avaliar prazos, garantias, multas e medição", risco="Contrato ruim ou execução deficitária", acao="Calcular risco econômico e operacional", prioridade="média"),
        ]
        for risco in riscos[:4]:
            itens.append(EditalChecklistItem(fase="risco", item=risco, risco=risco, acao="Mitigar antes da participação ou tratar em impugnação/esclarecimento", prioridade="alta"))
        for acao in blindagem[:3]:
            itens.append(EditalChecklistItem(fase="blindagem", item=acao, risco="Falha própria de habilitação/proposta", acao=acao, prioridade="alta"))
        for ataque in ataques[:3]:
            itens.append(EditalChecklistItem(fase="concorrentes", item=ataque, risco="Perder oportunidade de inabilitar/desclassificar concorrente", acao=ataque, prioridade="média"))
        return itens

    def _criterios_para_decision_engine(self, texto: str, riscos: list[str], restritivas: list[str], oportunidades: list[str], memoria: dict) -> DecisionCriteria:
        lower = texto.casefold()
        risco_hab = 70 if any(t in lower for t in ["atestado", "sicaf", "cat", "art", "rrt", "balanço", "balanco"]) else 45
        risco_jur = 70 if restritivas and any(t in lower for t in ["100%", "marca", "exclusivo", "somente", "sede"]) else 45
        oportunidade = 75 if oportunidades else 50
        risco_exec = 70 if any(t in lower for t in ["multa", "garantia", "prazo curto", "penalidade", "sanção", "sancao"]) else 40
        impugnacao = 75 if risco_jur >= 70 else 35
        historico = min(100, 45 + int(memoria.get("total") or 0) * 10)
        aderencia = 55
        chance = round((aderencia * 0.30) + (oportunidade * 0.30) + ((100 - risco_hab) * 0.20) + (historico * 0.20))
        return DecisionCriteria(
            aderencia_tecnica=aderencia,
            risco_habilitacao=risco_hab,
            risco_juridico=risco_jur,
            oportunidade_competitiva=oportunidade,
            risco_execucao=risco_exec,
            historico_memoria_viva=historico,
            necessidade_impugnacao=impugnacao,
            chance_estrategica_vitoria=max(0, min(100, chance)),
        )

    def _memoria_sugerida(self, decision_memory: MemorySuggestion | None, resumo: EditalResumo, riscos: list[str], oportunidades: list[str]) -> MemorySuggestion:
        if decision_memory:
            return decision_memory
        return MemorySuggestion(
            tipo="padrao",
            titulo="Análise estruturada de edital",
            descricao=f"Edital analisado com objeto: {resumo.objeto}",
            estrategia="Usar resumo, riscos, oportunidades, checklist e decisão recomendada para orientar Go/No-Go.",
            aprendizado="Editais devem alimentar o Decision Engine com riscos de habilitação, cláusulas restritivas, oportunidades de impugnação e pontos de ataque a concorrentes.",
            uso_futuro="Comparar com editais futuros de objeto/modalidade semelhante.",
            tags=["edital-analyzer", "edital", "decision-engine"],
        )

    def _sentencas_com_termos(self, texto: str, termos: list[str], limite: int = 10) -> list[str]:
        partes = re.split(r"(?<=[.;:])\s+", texto)
        achados = []
        for parte in partes:
            lower = parte.casefold()
            if any(termo in lower for termo in termos):
                achados.append(parte.strip())
            if len(achados) >= limite:
                break
        return achados
