from __future__ import annotations

import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4
from xml.etree import ElementTree

from fastapi import HTTPException, UploadFile, status

from app.schemas.case import CaseCreate
from app.schemas.edital import EditalAnalyzeTextRequest
from app.schemas.upload import UploadAnalyzeRequest, UploadAnalyzeResponse, UploadDocumentListResponse, UploadDocumentRecord, UploadDocumentUpdate, UploadResponse
from app.services.audit_log import audit_event
from app.services.case_engine import LiciCaseEngine
from app.services.edital_analyzer import LiciEditalAnalyzer
from app.services.memory_core_client import MemoryCoreClient
from app.services.upload_store import EDITAIS_DIR, HybridUploadStore

EXTENSOES_PERMITIDAS = {".pdf", ".docx", ".txt"}


class LiciUploadEngine:
    def __init__(
        self,
        store: HybridUploadStore | None = None,
        edital_analyzer: LiciEditalAnalyzer | None = None,
        case_engine: LiciCaseEngine | None = None,
        memory: MemoryCoreClient | None = None,
    ):
        self.store = store or HybridUploadStore()
        self.edital_analyzer = edital_analyzer or LiciEditalAnalyzer()
        self.case_engine = case_engine or LiciCaseEngine()
        self.memory = memory or MemoryCoreClient()

    def engine_info(self) -> dict[str, object]:
        return {
            "nome": "LICI Upload Engine",
            "objetivo": "Receber editais/documentos, extrair texto, registrar documento e enviar para análise automática.",
            "endpoints": [
                "GET /upload/engine",
                "POST /upload/edital",
                "GET /upload/documentos",
                "POST /upload/documentos/{id}/analisar",
            ],
            "formatos_aceitos": sorted(EXTENSOES_PERMITIDAS),
            "persistencia": {
                "arquivos": str(EDITAIS_DIR),
                "documentos": "/root/lici-app/storage/documentos.json",
            },
            "integracoes": ["Edital Analyzer", "Case Engine", "Decision Engine", "Memory Core", "Audit Log"],
        }

    def list_documents(self, organization_id: str | None = None, incluir_arquivados: bool = False) -> UploadDocumentListResponse:
        documentos = sorted(self.store.list(), key=lambda d: d.criado_em, reverse=True)
        if organization_id:
            documentos = [d for d in documentos if (d.organization_id or 'default-org') == organization_id]
        if not incluir_arquivados:
            documentos = [d for d in documentos if d.status != 'arquivado' and not (d.metadata or {}).get('arquivado')]
        return UploadDocumentListResponse(total=len(documentos), documentos=documentos)

    def get_document(self, document_id: str, organization_id: str | None = None) -> UploadDocumentRecord:
        document = self.store.get(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail='documento não encontrado')
        if organization_id and (document.organization_id or 'default-org') != organization_id:
            audit_event('security', 'acesso_negado_cross_org', 'erro', {'recurso': 'upload_document', 'document_id': document_id, 'organization_id': organization_id}, document_id)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Documento pertence a outra organização')
        return document

    def update_document(self, document_id: str, payload: UploadDocumentUpdate, organization_id: str | None = None) -> UploadDocumentRecord:
        document = self.get_document(document_id, organization_id=organization_id)
        data = document.model_dump()
        for key, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                data[key] = {**data.get(key, {}), **value} if key == 'metadata' else value
        data['atualizado_em'] = datetime.now(timezone.utc).isoformat()
        updated = self.store.update(UploadDocumentRecord(**data))
        audit_event('upload_engine', 'atualizacao_documento_upload', 'ok', {'status': updated.status, 'arquivo': updated.nome_original}, updated.id)
        return updated

    def archive_document(self, document_id: str, organization_id: str | None = None) -> UploadDocumentRecord:
        return self.update_document(document_id, UploadDocumentUpdate(status='arquivado', metadata={'arquivado': True, 'arquivado_em': datetime.now(timezone.utc).isoformat()}), organization_id=organization_id)

    def receive_edital(self, file: UploadFile, organization_id: str | None = None) -> UploadResponse:
        original_name = file.filename or "documento"
        ext = Path(original_name).suffix.casefold()
        if ext not in EXTENSOES_PERMITIDAS:
            audit_event("upload_engine", "upload_edital", "erro", {"erro": "extensão não permitida", "arquivo": original_name})
            raise HTTPException(status_code=400, detail="formato não suportado; envie PDF, DOCX ou TXT")

        safe_name = self._safe_filename(original_name)
        storage_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}-{safe_name}"
        path = EDITAIS_DIR / storage_name
        path.parent.mkdir(parents=True, exist_ok=True)

        size = self._save_upload(file.file, path)
        record = UploadDocumentRecord(
            organization_id=organization_id or 'default-org',
            nome_original=original_name,
            nome_arquivo=storage_name,
            caminho=str(path),
            content_type=file.content_type or "",
            extensao=ext.lstrip("."),
            tamanho_bytes=size,
            status="recebido",
        )

        try:
            texto = self._extract_text(path, ext)
            record.texto_extraido = texto
            record.caracteres_extraidos = len(texto)
            record.status = "texto_extraido" if texto.strip() else "erro"
            if not texto.strip():
                record.erro = "texto não extraído; documento pode estar escaneado ou protegido"
        except Exception as exc:
            record.status = "erro"
            record.erro = str(exc)

        created = self.store.create(record)
        audit_event(
            modulo="upload_engine",
            acao="upload_edital",
            status="ok" if created.status != "erro" else "erro",
            detalhes={
                "arquivo": created.nome_original,
                "caminho": created.caminho,
                "extensao": created.extensao,
                "tamanho_bytes": created.tamanho_bytes,
                "caracteres_extraidos": created.caracteres_extraidos,
                "erro": created.erro,
            },
            id_relacionado=created.id,
        )
        return UploadResponse(documento=created)

    def analyze_document(self, document_id: str, request: UploadAnalyzeRequest | None = None, organization_id: str | None = None) -> UploadAnalyzeResponse:
        request = request or UploadAnalyzeRequest()
        document = self.get_document(document_id, organization_id=organization_id)
        if not document.texto_extraido.strip():
            audit_event("upload_engine", "analise_documento", "erro", {"erro": "documento sem texto extraído"}, document_id)
            raise HTTPException(status_code=400, detail="documento sem texto extraído para análise")

        analise = self.edital_analyzer.analisar_texto(
            EditalAnalyzeTextRequest(
                texto=document.texto_extraido,
                termo_memoria=f"{request.orgao} {document.nome_original}",
                contexto_usuario=request.contexto_usuario,
                consultar_rag=request.consultar_rag,
            )
        )

        caso_id: str | None = None
        if request.criar_caso:
            caso = self.case_engine.create_case(
                CaseCreate(
                    cliente=request.cliente,
                    orgao=request.orgao or "Órgão não identificado",
                    objeto=analise.resumo_edital.objeto,
                    modalidade=request.modalidade or analise.resumo_edital.modalidade,
                    status=request.status,  # type: ignore[arg-type]
                    fase_atual=request.fase_atual,  # type: ignore[arg-type]
                    score_estrategico=analise.decisao_recomendada.score,
                    riscos=analise.riscos,
                    oportunidades=analise.oportunidades,
                    memorias_relacionadas=[],
                    contexto=f"Caso criado pelo Upload Engine a partir do documento {document.id}: {document.nome_original}",
                    texto_edital=document.texto_extraido,
                )
            )
            caso_id = caso.id

        memoria_sugerida = analise.memoria_sugerida.model_dump(mode="json") if analise.memoria_sugerida else None
        document.status = "analisado"
        document.atualizado_em = datetime.now(timezone.utc).isoformat()
        document.analise = analise.model_dump(mode="json")
        document.caso_id = caso_id or document.caso_id
        document.memoria_sugerida = memoria_sugerida
        updated = self.store.update(document)

        audit_event(
            modulo="upload_engine",
            acao="analise_documento",
            status="ok",
            detalhes={
                "documento": updated.nome_original,
                "decisao": analise.decisao_recomendada.decisao,
                "score": analise.decisao_recomendada.score,
                "caso_criado": bool(caso_id),
                "caso_id": caso_id,
                "memoria_sugerida": bool(memoria_sugerida),
            },
            id_relacionado=updated.id,
        )
        return UploadAnalyzeResponse(documento=updated, analise=analise, caso_id=caso_id, memoria_sugerida=memoria_sugerida)

    def _save_upload(self, source: BinaryIO, destination: Path) -> int:
        with destination.open("wb") as out:
            shutil.copyfileobj(source, out)
        return destination.stat().st_size

    def _extract_text(self, path: Path, ext: str) -> str:
        if ext == ".txt":
            return self._extract_txt(path)
        if ext == ".docx":
            return self._extract_docx(path)
        if ext == ".pdf":
            return self._extract_pdf_best_effort(path)
        raise ValueError("formato não suportado")

    def _extract_txt(self, path: Path) -> str:
        data = path.read_bytes()
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="ignore")

    def _extract_docx(self, path: Path) -> str:
        with zipfile.ZipFile(path) as docx:
            xml = docx.read("word/document.xml")
        root = ElementTree.fromstring(xml)
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        texts = [node.text for node in root.iter(f"{ns}t") if node.text]
        return "\n".join(texts)

    def _extract_pdf_best_effort(self, path: Path) -> str:
        raw = path.read_bytes()
        text = raw.decode("latin-1", errors="ignore")
        chunks = re.findall(r"\(([^()]{2,})\)\s*Tj", text)
        chunks.extend(re.findall(r"\(([^()]{2,})\)", text))
        cleaned = "\n".join(self._decode_pdf_literal(chunk) for chunk in chunks)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            return cleaned
        # Fallback mínimo: extrai sequências textuais legíveis do binário.
        ascii_runs = re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9\s,.;:/()%ºª°\-]{20,}", text)
        return "\n".join(run.strip() for run in ascii_runs[:200])

    def _decode_pdf_literal(self, value: str) -> str:
        return (
            value.replace(r"\(", "(")
            .replace(r"\)", ")")
            .replace(r"\n", "\n")
            .replace(r"\r", "\n")
            .replace(r"\t", "\t")
            .replace(r"\\", "\\")
        )

    def _safe_filename(self, filename: str) -> str:
        name = Path(filename).name.strip() or "documento"
        return re.sub(r"[^A-Za-z0-9À-ÿ._-]+", "-", name)[:160]
