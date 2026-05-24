from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.schemas.decision import DecisionRequest
from app.schemas.document_generator import DocumentGenerateRequest, DocumentGenerateResponse, GeneratedDocumentListResponse, GeneratedDocumentRecord, GeneratedDocumentUpdate
from app.schemas.edital import EditalAnalyzeTextRequest
from app.schemas.memory import MemoryCreate
from app.services.audit_log import audit_event
from app.services.case_store import JsonCaseStore
from app.services.decision_engine import LiciDecisionEngine
from app.services.document_generator_store import GENERATED_DIR, HybridGeneratedDocumentStore
from app.services.edital_analyzer import LiciEditalAnalyzer
from app.services.memory_core_client import MemoryCoreClient
from app.services.upload_store import HybridUploadStore


class LiciDocumentGenerator:
    def __init__(
        self,
        store: HybridGeneratedDocumentStore | None = None,
        case_store: JsonCaseStore | None = None,
        upload_store: HybridUploadStore | None = None,
        edital_analyzer: LiciEditalAnalyzer | None = None,
        decision_engine: LiciDecisionEngine | None = None,
        memory: MemoryCoreClient | None = None,
    ):
        self.store = store or HybridGeneratedDocumentStore()
        self.case_store = case_store or JsonCaseStore()
        self.upload_store = upload_store or HybridUploadStore()
        self.edital_analyzer = edital_analyzer or LiciEditalAnalyzer()
        self.decision_engine = decision_engine or LiciDecisionEngine()
        self.memory = memory or MemoryCoreClient()

    def engine_info(self) -> dict[str, object]:
        return {
            "nome": "LICI Document Generator",
            "objetivo": "Gerar peças administrativas a partir da análise estratégica da LICI.",
            "endpoints": [
                "GET /documentos/engine",
                "POST /documentos/gerar-impugnacao",
                "POST /documentos/gerar-recurso",
                "POST /documentos/gerar-contrarrazoes",
                "GET /documentos/gerados",
            ],
            "tipos": ["impugnacao", "recurso", "contrarrazoes"],
            "persistencia": str(GENERATED_DIR),
            "integracoes": ["Upload Engine", "Edital Analyzer", "Case Engine", "Decision Engine", "Memory Core", "Audit Log"],
        }

    def list_generated(self, organization_id: str | None = None, incluir_arquivados: bool = False) -> GeneratedDocumentListResponse:
        docs = self.store.list(organization_id=organization_id)
        if not incluir_arquivados:
            docs = [d for d in docs if not (d.metadata or {}).get('arquivado')]
        return GeneratedDocumentListResponse(total=len(docs), documentos=docs)

    def get_generated(self, document_id: str, organization_id: str | None = None) -> GeneratedDocumentRecord:
        doc = self.store.get(document_id, organization_id=organization_id)
        if doc:
            return doc
        if self.store.exists(document_id):
            audit_event('security', 'acesso_negado_cross_org', 'erro', {'recurso': 'documento_gerado', 'document_id': document_id, 'organization_id': organization_id}, document_id)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Documento pertence a outra organização')
        raise HTTPException(status_code=404, detail='documento gerado não encontrado')

    def update_generated(self, document_id: str, payload: GeneratedDocumentUpdate, organization_id: str | None = None) -> GeneratedDocumentRecord:
        doc = self.get_generated(document_id, organization_id=organization_id)
        data = doc.model_dump()
        for key, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                data[key] = {**data.get(key, {}), **value} if key == 'metadata' else value
        saved = self.store.update(GeneratedDocumentRecord(**data))
        audit_event('document_generator', 'atualizacao_documento_gerado', 'ok', {'titulo': saved.titulo, 'tipo': saved.tipo}, saved.id)
        return saved

    def archive_generated(self, document_id: str, organization_id: str | None = None) -> GeneratedDocumentRecord:
        return self.update_generated(document_id, GeneratedDocumentUpdate(metadata={'arquivado': True, 'arquivado_em': datetime.now(timezone.utc).isoformat()}), organization_id=organization_id)

    def gerar_impugnacao(self, request: DocumentGenerateRequest, organization_id: str | None = None) -> DocumentGenerateResponse:
        if organization_id and not request.organization_id:
            request = request.model_copy(update={"organization_id": organization_id})
        ctx = self._context(request)
        texto = self._template_impugnacao(ctx)
        return self._persist("impugnacao", "Impugnação administrativa", texto, request, ctx)

    def gerar_recurso(self, request: DocumentGenerateRequest, organization_id: str | None = None) -> DocumentGenerateResponse:
        if organization_id and not request.organization_id:
            request = request.model_copy(update={"organization_id": organization_id})
        ctx = self._context(request)
        texto = self._template_recurso(ctx)
        return self._persist("recurso", "Recurso administrativo", texto, request, ctx)

    def gerar_contrarrazoes(self, request: DocumentGenerateRequest, organization_id: str | None = None) -> DocumentGenerateResponse:
        if organization_id and not request.organization_id:
            request = request.model_copy(update={"organization_id": organization_id})
        ctx = self._context(request)
        texto = self._template_contrarrazoes(ctx)
        return self._persist("contrarrazoes", "Contrarrazões administrativas", texto, request, ctx)

    def _context(self, request: DocumentGenerateRequest) -> dict[str, Any]:
        organization_id = request.organization_id or "default-org"
        case = self.case_store.get(request.case_id, organization_id=organization_id) if request.case_id else None
        upload_doc = self.upload_store.get(request.documento_id) if request.documento_id else None
        if request.case_id and case is None:
            raise HTTPException(status_code=404, detail="caso vivo não encontrado")
        if request.documento_id and upload_doc is None:
            raise HTTPException(status_code=404, detail="documento de upload não encontrado")

        analise = dict(request.analise or {})
        if not analise and upload_doc and upload_doc.analise:
            analise = upload_doc.analise
        if not analise and upload_doc and upload_doc.texto_extraido:
            analise = self.edital_analyzer.analisar_texto(
                EditalAnalyzeTextRequest(texto=upload_doc.texto_extraido, termo_memoria=request.orgao or upload_doc.nome_original, consultar_rag=False)
            ).model_dump(mode="json")
        if not analise and case and case.texto_edital:
            analise = self.edital_analyzer.analisar_texto(
                EditalAnalyzeTextRequest(texto=case.texto_edital, termo_memoria=case.orgao, consultar_rag=False)
            ).model_dump(mode="json")

        resumo = analise.get("resumo_edital") or {}
        decisao = analise.get("decisao_recomendada") or {}
        riscos = analise.get("riscos") or (case.riscos if case else []) or []
        oportunidades = analise.get("oportunidades") or (case.oportunidades if case else []) or []
        restritivas = analise.get("clausulas_restritivas") or []
        impugnacao = analise.get("oportunidades_impugnacao") or []
        ataques = analise.get("pontos_ataque_concorrentes") or []

        objeto = request.objeto or (case.objeto if case else "") or resumo.get("objeto") or "Objeto não identificado"
        orgao = request.orgao or (case.orgao if case else "") or "Órgão/Entidade não informado"
        modalidade = request.modalidade or (case.modalidade if case else "") or resumo.get("modalidade") or "Modalidade não informada"

        pergunta_decisao = f"Gerar peça administrativa para {orgao}; objeto {objeto}; tese {request.tese_principal}; riscos {riscos}; oportunidades {oportunidades}"
        decision = self.decision_engine.decidir(DecisionRequest(pergunta=pergunta_decisao, termo_memoria=f"{orgao} {objeto}", consultar_rag=False))

        tese = request.tese_principal or self._pick_first(impugnacao, restritivas, riscos, default="exigência editalícia/decisão administrativa que restringe competitividade ou viola julgamento objetivo")
        fundamentos = request.fundamentos or self._fundamentos_padrao(tese, riscos, restritivas)
        pedidos = request.pedidos or self._pedidos_padrao()

        return {
            "case": case,
            "upload_doc": upload_doc,
            "analise": analise,
            "orgao": orgao,
            "cliente": request.cliente or (case.cliente if case else "Interessada"),
            "processo": request.processo or "Processo/Edital não informado",
            "modalidade": modalidade,
            "objeto": objeto,
            "recorrente": request.recorrente or request.cliente or (case.cliente if case else "Interessada"),
            "recorrido": request.recorrido or "Licitante recorrida/decisão administrativa",
            "autoridade": request.autoridade,
            "fatos": request.fatos or self._fatos_padrao(objeto, riscos, oportunidades),
            "tese": tese,
            "fundamentos": fundamentos,
            "pedidos": pedidos,
            "riscos": riscos,
            "oportunidades": oportunidades,
            "restritivas": restritivas,
            "ataques": ataques,
            "decision": decision,
        }

    def _persist(self, tipo: str, titulo: str, texto: str, request: DocumentGenerateRequest, ctx: dict[str, Any]) -> DocumentGenerateResponse:
        now = datetime.now(timezone.utc)
        safe = self._safe_slug(f"{tipo}-{ctx['orgao']}-{now.strftime('%Y%m%d-%H%M%S')}")
        arquivo = f"{safe}.txt"
        caminho = str(Path(GENERATED_DIR) / arquivo)
        memoria = self._memoria_sugerida(tipo, ctx)
        if request.registrar_memoria:
            self.memory.registrar(memoria)

        record = GeneratedDocumentRecord(
            organization_id=request.organization_id or "default-org",
            tipo=tipo,  # type: ignore[arg-type]
            titulo=titulo,
            arquivo=arquivo,
            caminho=caminho,
            texto=texto,
            cliente=ctx["cliente"],
            orgao=ctx["orgao"],
            processo=ctx["processo"],
            modalidade=ctx["modalidade"],
            objeto=ctx["objeto"],
            case_id=request.case_id,
            documento_id=request.documento_id,
            decisao_base=ctx["decision"].decisao,
            score_base=ctx["decision"].score,
            memoria_sugerida=memoria,
            metadata={"registrar_memoria": request.registrar_memoria},
        )
        created = self.store.create(record)
        audit_event(
            modulo="document_generator",
            acao=f"geracao_{tipo}",
            status="ok",
            detalhes={"arquivo": created.arquivo, "orgao": created.orgao, "case_id": request.case_id, "documento_id": request.documento_id, "memoria_sugerida": True},
            id_relacionado=created.id,
        )
        return DocumentGenerateResponse(documento=created, memoria_sugerida=memoria)

    def _template_header(self, ctx: dict[str, Any], titulo: str) -> str:
        return f"""AO(À) {ctx['autoridade'].upper()}\n{ctx['orgao'].upper()}\n\nReferência: {ctx['processo']}\nModalidade: {ctx['modalidade']}\nObjeto: {ctx['objeto']}\n\n{titulo}\n\n{ctx['cliente']}, pessoa jurídica interessada no certame em referência, vem, respeitosamente, apresentar a presente manifestação administrativa, pelos fundamentos a seguir expostos.\n"""

    def _template_impugnacao(self, ctx: dict[str, Any]) -> str:
        return self._assemble(ctx, "IMPUGNAÇÃO AO EDITAL", [
            ("I. SÍNTESE DO EDITAL E DO PONTO IMPUGNADO", ctx["fatos"]),
            ("II. ILEGALIDADE/RESTRIÇÃO IDENTIFICADA", f"A tese central é: {ctx['tese']}. A exigência/condição deve ser revista quando restringe a competitividade, não guarda proporcionalidade com o objeto ou não possui justificativa técnica suficiente."),
            ("III. FUNDAMENTOS", self._bullets(ctx["fundamentos"])),
            ("IV. RISCOS OPERACIONAIS MAPEADOS PELA LICI", self._bullets(ctx["riscos"])),
            ("V. PEDIDOS", self._bullets(ctx["pedidos"])),
        ])

    def _template_recurso(self, ctx: dict[str, Any]) -> str:
        return self._assemble(ctx, "RECURSO ADMINISTRATIVO", [
            ("I. TEMPESTIVIDADE E CABIMENTO", "O presente recurso é apresentado contra decisão praticada no curso do certame, buscando preservar julgamento objetivo, isonomia, vinculação ao edital e seleção da proposta mais vantajosa."),
            ("II. FATOS RELEVANTES", ctx["fatos"]),
            ("III. RAZÕES RECURSAIS", f"A tese recursal principal é: {ctx['tese']}. A decisão deve ser reformada diante dos vícios/falhas objetivas demonstrados."),
            ("IV. FUNDAMENTOS", self._bullets(ctx["fundamentos"])),
            ("V. PEDIDOS", self._bullets(ctx["pedidos"])),
        ])

    def _template_contrarrazoes(self, ctx: dict[str, Any]) -> str:
        return self._assemble(ctx, "CONTRARRAZÕES AO RECURSO ADMINISTRATIVO", [
            ("I. SÍNTESE", f"As presentes contrarrazões buscam manter a decisão administrativa atacada por {ctx['recorrido']}, preservando o edital, a isonomia e o julgamento objetivo."),
            ("II. REGULARIDADE DA CONDUTA/PROPOSTA", ctx["fatos"]),
            ("III. IMPROCEDÊNCIA DA TESE ADVERSA", f"A tese defensiva central é: {ctx['tese']}. O recurso adverso não demonstra vício material suficiente para alterar o resultado."),
            ("IV. FUNDAMENTOS", self._bullets(ctx["fundamentos"])),
            ("V. PEDIDOS", self._bullets(["receber as presentes contrarrazões", "negar provimento ao recurso adverso", "manter a decisão recorrida e o resultado do certame"])),
        ])

    def _assemble(self, ctx: dict[str, Any], titulo: str, sections: list[tuple[str, str]]) -> str:
        parts = [self._template_header(ctx, titulo)]
        for heading, body in sections:
            parts.append(f"\n{heading}\n\n{body}\n")
        parts.append("\nTermos em que, pede deferimento.\n\n[local], [data].\n\n__________________________________\nRepresentante legal\n")
        return "\n".join(parts)

    def _memoria_sugerida(self, tipo: str, ctx: dict[str, Any]) -> dict[str, Any]:
        return MemoryCreate(
            tipo="tese",
            titulo=f"Peça {tipo}: {ctx['tese'][:90]}",
            descricao=f"Documento {tipo} gerado para {ctx['orgao']} no objeto {ctx['objeto']}.",
            contexto=f"Processo {ctx['processo']} | modalidade {ctx['modalidade']}",
            estrategia="Reutilizar tese, fundamentos e pedidos em editais/casos com padrão semelhante.",
            aprendizado=f"Tese administrativa estruturada: {ctx['tese']}",
            uso_futuro="Base para impugnações, recursos ou contrarrazões futuras em órgãos/objetos similares.",
            tags=["document-generator", tipo, ctx["orgao"]],
            fonte="LICI Document Generator",
            confianca=0.7,
        ).model_dump(mode="json")

    def _pick_first(self, *lists: Any, default: str) -> str:
        for items in lists:
            if isinstance(items, list) and items:
                return str(items[0])
            if isinstance(items, str) and items:
                return items
        return default

    def _fundamentos_padrao(self, tese: str, riscos: list[str], restritivas: list[str]) -> list[str]:
        fundamentos = [
            "Lei 14.133/2021: observância à isonomia, competitividade, julgamento objetivo, motivação e seleção da proposta mais vantajosa.",
            "Vinculação ao edital não autoriza manutenção de cláusula restritiva, desproporcional ou sem justificativa técnica adequada.",
            f"Tese operacional: {tese}.",
        ]
        fundamentos.extend(str(item) for item in (restritivas or riscos)[:3])
        return fundamentos

    def _pedidos_padrao(self) -> list[str]:
        return [
            "recebimento e conhecimento da presente peça administrativa",
            "suspensão do certame, se necessário, até decisão fundamentada",
            "retificação do edital/decisão administrativa no ponto impugnado/recorrido",
            "reabertura de prazo quando a alteração impactar a formulação de propostas",
            "publicação de decisão motivada e comunicação aos interessados",
        ]

    def _fatos_padrao(self, objeto: str, riscos: list[str], oportunidades: list[str]) -> str:
        return (
            f"A LICI analisou o certame cujo objeto é {objeto}. "
            f"Foram identificados os seguintes riscos: {self._join(riscos)}. "
            f"Também foram identificadas oportunidades/elementos estratégicos: {self._join(oportunidades)}."
        )

    def _bullets(self, items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items if item) or "- Ponto a complementar com documentos do caso concreto."

    def _join(self, items: list[str]) -> str:
        return "; ".join(str(item) for item in items if item) or "não especificados automaticamente"

    def _safe_slug(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9À-ÿ._-]+", "-", value).strip("-.").lower()
        return slug[:140] or "documento-gerado"
