from __future__ import annotations

import json
import os
import re
import shutil
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, BinaryIO, TypeVar
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel

from app.schemas.company_document import (
    CompanyChecklistRequest,
    CompanyChecklistResponse,
    CompanyDocument,
    CompanyDocumentAlert,
    CompanyDocumentCreate,
    CompanyDocumentDashboard,
    CompanyDocumentUpdate,
    CompanyDocumentVersion,
    CompanyDossier,
    DOCUMENT_TYPES,
)
from app.services.audit_log import audit_event
from app.services.observability import structured_log
from app.services.upload_store import HybridUploadStore

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

ROOT = Path('/root/lici-app/company_documents')
FILES_ROOT = ROOT / 'files'
DOCS_JSON = ROOT / 'documents.json'
VERSIONS_JSON = ROOT / 'versions.json'
ALERTS_JSON = ROOT / 'alerts.json'
POSTGRES_ENV_FILE = Path('/root/lici-app/secrets/postgres.env')
T = TypeVar('T', bound=BaseModel)


class DocumentalHybridStore:
    def __init__(self, model: type[T], path: Path, table: str, module: str = 'documental'):
        self.model = model
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_json([])
        self.table = table
        self.module = module
        self.dsn = os.getenv('LICI_DATABASE_URL') or self._dsn_from_env_file()
        self._available_cache = {'checked_at': 0.0, 'available': False}
        self._table_ready = False

    def available(self) -> bool:
        if not psycopg or not self.dsn:
            return False
        now = time.time()
        if now - self._available_cache['checked_at'] <= 15:
            return bool(self._available_cache['available'])
        try:
            with psycopg.connect(self.dsn, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
                    cur.fetchone()
            self._available_cache = {'checked_at': now, 'available': True}
            return True
        except Exception:
            self._available_cache = {'checked_at': now, 'available': False}
            return False

    def list(self, organization_id: str, limit: int = 200, offset: int = 0, **filters: Any) -> list[T]:
        limit = max(1, min(int(limit or 200), 1000)); offset = max(0, int(offset or 0))
        try:
            if self.available():
                self._ensure_table()
                with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
                    with conn.cursor() as cur:
                        where = ['organization_id = %s']; params: list[Any] = [organization_id]
                        for key in ['empresa_id', 'cliente_id', 'status', 'tipo_documental', 'escopo', 'document_id']:
                            value = filters.get(key)
                            if value:
                                where.append(f'{key} = %s'); params.append(value)
                        sql = f"SELECT raw_payload FROM {self.table} WHERE " + ' AND '.join(where) + ' ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST LIMIT %s OFFSET %s'
                        params.extend([limit, offset]); cur.execute(sql, params)
                        return [self.model(**self._raw(r['raw_payload'])) for r in cur.fetchall()]
            audit_event(self.module, 'postgres_fallback_json', 'erro', {'operacao': f'list_{self.table}', 'motivo': 'postgres_indisponivel'})
        except Exception as exc:
            audit_event(self.module, 'postgres_fallback_json', 'erro', {'operacao': f'list_{self.table}', 'erro': str(exc)})
        items = [i for i in self._read_json() if (getattr(i, 'organization_id', None) or 'default-org') == organization_id]
        for key, value in filters.items():
            if value:
                items = [i for i in items if getattr(i, key, None) == value]
        return sorted(items, key=lambda i: str(getattr(i, 'atualizado_em', None) or getattr(i, 'criado_em', None)), reverse=True)[offset:offset + limit]

    def get(self, item_id: str, organization_id: str | None = None) -> T | None:
        try:
            if self.available():
                self._ensure_table()
                with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
                    with conn.cursor() as cur:
                        if organization_id:
                            cur.execute(f'SELECT raw_payload FROM {self.table} WHERE id=%s AND organization_id=%s', (item_id, organization_id))
                        else:
                            cur.execute(f'SELECT raw_payload FROM {self.table} WHERE id=%s', (item_id,))
                        row = cur.fetchone()
                        if row: return self.model(**self._raw(row['raw_payload']))
        except Exception as exc:
            audit_event(self.module, 'postgres_fallback_json', 'erro', {'operacao': f'get_{self.table}', 'erro': str(exc)}, item_id)
        for item in self._read_json():
            if item.id == item_id and (not organization_id or (getattr(item, 'organization_id', None) or 'default-org') == organization_id):
                return item
        return None

    def exists(self, item_id: str) -> bool:
        return self.get(item_id) is not None

    def upsert(self, item: T) -> T:
        items = self._read_json(); found = False
        for idx, cur in enumerate(items):
            if cur.id == item.id:
                items[idx] = item; found = True; break
        if not found: items.append(item)
        self._write_json([i.model_dump() for i in items])
        try:
            if self.available():
                self._ensure_table()
                data = item.model_dump(); org = getattr(item, 'organization_id', 'default-org') or 'default-org'
                with psycopg.connect(self.dsn, connect_timeout=3) as conn:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            cur.execute(f'''
                                INSERT INTO {self.table} (id, organization_id, empresa_id, cliente_id, status, tipo_documental, document_id, raw_payload, created_at, updated_at)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                                ON CONFLICT (id) DO UPDATE SET organization_id=EXCLUDED.organization_id, empresa_id=EXCLUDED.empresa_id,
                                  cliente_id=EXCLUDED.cliente_id, status=EXCLUDED.status, tipo_documental=EXCLUDED.tipo_documental,
                                  document_id=EXCLUDED.document_id, raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at
                            ''', (
                                item.id, org, getattr(item, 'empresa_id', None), getattr(item, 'cliente_id', None), getattr(item, 'status', ''),
                                getattr(item, 'tipo_documental', ''), getattr(item, 'document_id', None), json.dumps(data, ensure_ascii=False, default=str),
                                getattr(item, 'criado_em', None), getattr(item, 'atualizado_em', getattr(item, 'criado_em', None)),
                            ))
                audit_event(self.module, 'dual_write_postgres', 'ok', {'tabela': self.table}, item.id)
            else:
                audit_event(self.module, 'dual_write_postgres', 'erro', {'tabela': self.table, 'motivo': 'postgres_indisponivel'}, item.id)
        except Exception as exc:
            audit_event(self.module, 'dual_write_postgres', 'erro', {'tabela': self.table, 'erro': str(exc)}, item.id)
        return item

    def _ensure_table(self) -> None:
        if self._table_ready: return
        if not psycopg or not self.dsn: raise RuntimeError('PostgreSQL indisponível')
        with psycopg.connect(self.dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.table} (
                        id TEXT PRIMARY KEY,
                        organization_id TEXT NOT NULL DEFAULT 'default-org',
                        empresa_id TEXT,
                        cliente_id TEXT,
                        status TEXT NOT NULL DEFAULT '',
                        tipo_documental TEXT NOT NULL DEFAULT '',
                        document_id TEXT,
                        raw_payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ,
                        updated_at TIMESTAMPTZ
                    )
                ''')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_org_status ON {self.table} (organization_id, status)')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_org_empresa ON {self.table} (organization_id, empresa_id)')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_org_cliente ON {self.table} (organization_id, cliente_id)')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_org_tipo ON {self.table} (organization_id, tipo_documental)')
            conn.commit()
        self._table_ready = True

    def _read_json(self) -> list[T]:
        try: raw = json.loads(self.path.read_text(encoding='utf-8'))
        except Exception: raw = []
        return [self.model(**i) for i in raw]

    def _write_json(self, data: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile('w', encoding='utf-8', dir=self.path.parent, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2, default=str); tmp.write('\n'); tmp_path = Path(tmp.name)
        os.chmod(tmp_path, 0o600); tmp_path.replace(self.path)

    def _raw(self, raw: Any) -> dict[str, Any]:
        return json.loads(raw) if isinstance(raw, str) else dict(raw or {})

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding='utf-8').splitlines():
                if line.startswith('LICI_DATABASE_URL='): return line.split('=', 1)[1].strip()
        except FileNotFoundError: return None
        return None


class LiciCompanyDocumentService:
    def __init__(self):
        self.docs = DocumentalHybridStore(CompanyDocument, DOCS_JSON, 'company_documents')
        self.versions = DocumentalHybridStore(CompanyDocumentVersion, VERSIONS_JSON, 'company_document_versions')
        self.alerts = DocumentalHybridStore(CompanyDocumentAlert, ALERTS_JSON, 'company_document_alerts')
        self.upload_store = HybridUploadStore()
        FILES_ROOT.mkdir(parents=True, exist_ok=True); os.chmod(FILES_ROOT, 0o700)
        self._ensure_postgres_tables()

    def _ensure_postgres_tables(self) -> None:
        for store in (self.docs, self.versions, self.alerts):
            try:
                if store.available():
                    store._ensure_table()
            except Exception as exc:
                audit_event('documental', 'postgres_schema_documental', 'erro', {'tabela': store.table, 'erro': str(exc)})

    def info(self) -> dict[str, Any]:
        self._ensure_postgres_tables()
        return {'nome': 'Documental Empresarial 360°', 'fase': 'Fase 1', 'status': 'ativo', 'sem_ia_livre': True, 'tabelas': ['company_documents', 'company_document_versions', 'company_document_alerts'], 'filesystem': str(FILES_ROOT), 'fallback_json': [str(DOCS_JSON), str(VERSIONS_JSON), str(ALERTS_JSON)], 'tipos_documentais': DOCUMENT_TYPES}

    def list_documents(self, organization_id: str, limit: int = 200, offset: int = 0, **filters: Any) -> list[CompanyDocument]:
        docs = self.docs.list(organization_id, limit=limit, offset=offset, **filters)
        changed = False
        out = []
        for doc in docs:
            normalized = self._normalize_doc(doc)
            if normalized.status != doc.status or normalized.risco_documental != doc.risco_documental or normalized.score_documental != doc.score_documental:
                self.docs.upsert(normalized); changed = True
            out.append(normalized)
        if changed: self._generate_alerts(organization_id, out)
        return out

    def create_document(self, payload: CompanyDocumentCreate, organization_id: str) -> CompanyDocument:
        doc = CompanyDocument(**payload.model_dump(), organization_id=organization_id or 'default-org')
        doc = self._normalize_doc(doc)
        saved = self.docs.upsert(doc)
        self._generate_alerts(saved.organization_id, [saved])
        audit_event('documental', 'documento_criado', 'ok', {'tipo': saved.tipo_documental, 'empresa': saved.empresa_nome, 'status': saved.status}, saved.id)
        structured_log('api', 'documental_documento_criado', 'ok', {'id': saved.id, 'organization_id': saved.organization_id})
        return saved

    def upload_document(self, file: UploadFile, organization_id: str, payload: CompanyDocumentCreate) -> CompanyDocument:
        doc = CompanyDocument(**payload.model_dump(), organization_id=organization_id or 'default-org')
        safe = self._safe_filename(file.filename or 'documento')
        ext = Path(safe).suffix.lower()
        if ext not in {'.pdf', '.docx', '.txt', '.png', '.jpg', '.jpeg', '.webp', '.xlsx', '.csv'}:
            raise HTTPException(status_code=400, detail='formato não suportado para repositório documental')
        folder = FILES_ROOT / doc.organization_id / (doc.empresa_id or doc.cliente_id or 'sem-vinculo') / doc.tipo_documental
        folder.mkdir(parents=True, exist_ok=True); os.chmod(folder, 0o700)
        filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}-{safe}"
        path = folder / filename
        with path.open('wb') as out:
            shutil.copyfileobj(file.file, out)
        os.chmod(path, 0o600)
        doc.arquivo_nome = file.filename or filename
        doc.arquivo_caminho = str(path)
        doc.content_type = file.content_type or ''
        doc.tamanho_bytes = path.stat().st_size
        doc = self._normalize_doc(doc)
        saved = self.docs.upsert(doc)
        self.versions.upsert(CompanyDocumentVersion(organization_id=saved.organization_id, document_id=saved.id, versao=saved.versao_atual, arquivo_nome=saved.arquivo_nome, arquivo_caminho=saved.arquivo_caminho, content_type=saved.content_type, tamanho_bytes=saved.tamanho_bytes))
        self._generate_alerts(saved.organization_id, [saved])
        audit_event('documental', 'upload_documento', 'ok', {'arquivo': saved.arquivo_nome, 'tipo': saved.tipo_documental, 'tamanho_bytes': saved.tamanho_bytes}, saved.id)
        structured_log('api', 'documental_upload', 'ok', {'id': saved.id, 'bytes': saved.tamanho_bytes, 'organization_id': saved.organization_id})
        return saved

    def update_document(self, document_id: str, payload: CompanyDocumentUpdate, organization_id: str) -> CompanyDocument:
        doc = self.docs.get(document_id, organization_id)
        if not doc:
            if self.docs.exists(document_id):
                audit_event('documental', 'cross_org_bloqueado', 'erro', {'document_id': document_id, 'organization_id': organization_id}, document_id)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Documento pertence a outra organização')
            raise HTTPException(status_code=404, detail='Documento não encontrado')
        data = doc.model_dump()
        for key, value in payload.model_dump(exclude_unset=True).items(): data[key] = value
        data['atualizado_em'] = datetime.now(timezone.utc)
        updated = self._normalize_doc(CompanyDocument(**data))
        saved = self.docs.upsert(updated)
        self._generate_alerts(saved.organization_id, [saved])
        audit_event('documental', 'documento_atualizado', 'ok', {'status': saved.status, 'risco_documental': saved.risco_documental}, saved.id)
        return saved

    def dashboard(self, organization_id: str) -> CompanyDocumentDashboard:
        docs = self.list_documents(organization_id, limit=1000)
        alerts = self._generate_alerts(organization_id, docs)
        empresas_risco = {d.empresa_id or d.empresa_nome or d.cliente_id or d.cliente_nome for d in docs if d.status in {'vencido', 'inválido', 'pendente'} or d.risco_documental >= 70}
        scores = [d.score_documental for d in docs]
        return CompanyDocumentDashboard(
            total_documentos=len(docs),
            documentos_vencendo=len([d for d in docs if d.status == 'vencendo']),
            documentos_vencidos=len([d for d in docs if d.status == 'vencido']),
            empresas_em_risco=len(empresas_risco),
            score_documental_medio=round(sum(scores) / max(len(scores), 1), 2),
            alertas_criticos=len([a for a in alerts if a.severidade == 'critica' and a.status == 'ativo']),
            atestados_estrategicos=len([d for d in docs if d.tipo_documental == 'atestado' and d.score_documental >= 70]),
            por_status=dict(Counter(d.status for d in docs)),
            por_tipo=dict(Counter(d.tipo_documental for d in docs)),
            documentos_criticos=sorted([d for d in docs if d.criticidade in {'alta','critica'} or d.risco_documental >= 60], key=lambda d: d.risco_documental, reverse=True)[:20],
            alertas=alerts[:30],
        )

    def dossier(self, organization_id: str, empresa_id: str | None = None, empresa_nome: str = '') -> CompanyDossier:
        docs = self.list_documents(organization_id, limit=1000)
        if empresa_id: docs = [d for d in docs if d.empresa_id == empresa_id or d.cliente_id == empresa_id]
        elif empresa_nome: docs = [d for d in docs if empresa_nome.lower() in (d.empresa_nome or d.cliente_nome or '').lower()]
        nome = empresa_nome or (docs[0].empresa_nome or docs[0].cliente_nome if docs else 'empresa')
        validos = len([d for d in docs if d.status == 'válido'])
        pend = len([d for d in docs if d.status in {'pendente','inválido'}])
        riscos = len([d for d in docs if d.status in {'vencido','vencendo'} or d.risco_documental >= 60])
        score = self._score_empresa(docs)
        apt = 'apta' if score >= 75 and pend == 0 and not [d for d in docs if d.status == 'vencido'] else ('atenção' if score >= 50 else 'risco de inabilitação')
        return CompanyDossier(empresa_id=empresa_id, empresa_nome=nome, documentos_validos=validos, pendencias=pend, riscos=riscos, vencimentos=[d for d in docs if d.status in {'vencendo','vencido'}], capacidade_tecnica=[d for d in docs if d.tipo_documental == 'atestado'], score_documental=score, aptidao_licitatoria=apt, documentos=docs[:200])

    def checklist(self, organization_id: str, request: CompanyChecklistRequest) -> CompanyChecklistResponse:
        docs = self.list_documents(organization_id, limit=1000)
        if request.empresa_id: docs = [d for d in docs if d.empresa_id == request.empresa_id or d.cliente_id == request.empresa_id]
        elif request.empresa_nome: docs = [d for d in docs if request.empresa_nome.lower() in (d.empresa_nome or d.cliente_nome or '').lower()]
        edital_text = request.edital_texto or ''
        if request.upload_document_id:
            upload = self.upload_store.get(request.upload_document_id)
            edital_text = edital_text or (upload.texto_extraido if upload else '')
        exigidos = request.tipos_exigidos or self._infer_required_types(edital_text)
        presentes = sorted({d.tipo_documental for d in docs if d.tipo_documental in exigidos and d.status in {'válido','vencendo'}})
        faltantes = [t for t in exigidos if t not in presentes]
        vencidos = sorted({d.tipo_documental for d in docs if d.tipo_documental in exigidos and d.status == 'vencido'})
        score = self._score_empresa(docs)
        risco = 'alto' if faltantes or vencidos else ('médio' if any(d.status == 'vencendo' for d in docs if d.tipo_documental in exigidos) else 'baixo')
        sugestoes = [f'Regularizar/anexar {t} antes da habilitação.' for t in faltantes + vencidos]
        if not sugestoes: sugestoes = ['Dossiê documental aparentemente aderente; revisar exigências específicas do edital antes da sessão.']
        audit_event('documental', 'checklist_licitacao', 'ok', {'empresa': request.empresa_nome, 'faltantes': faltantes, 'vencidos': vencidos, 'risco': risco}, request.empresa_id)
        return CompanyChecklistResponse(empresa_nome=request.empresa_nome or (docs[0].empresa_nome if docs else ''), exigidos=exigidos, presentes=presentes, faltantes=faltantes, vencidos=vencidos, risco_inabilitacao=risco, sugestoes_regularizacao=sugestoes, score_documental=score)

    def _normalize_doc(self, doc: CompanyDocument) -> CompanyDocument:
        days = self._days_to_expiry(doc.validade)
        if doc.status == 'arquivado':
            doc.risco_documental = 0
            doc.score_documental = 0
            doc.atualizado_em = datetime.now(timezone.utc)
            return doc
        if doc.status not in {'pendente', 'inválido'}:
            if days is not None and days < 0: doc.status = 'vencido'
            elif days is not None and days <= 30: doc.status = 'vencendo'
            elif doc.arquivo_caminho or doc.payload: doc.status = 'válido'
        risk = 10
        if doc.status == 'vencido': risk = 95
        elif doc.status == 'inválido': risk = 90
        elif doc.status == 'pendente': risk = 75
        elif doc.status == 'vencendo': risk = 55
        if doc.criticidade == 'critica': risk += 10
        elif doc.criticidade == 'alta': risk += 5
        doc.risco_documental = min(risk, 100)
        doc.score_documental = max(0, 100 - doc.risco_documental)
        doc.atualizado_em = datetime.now(timezone.utc)
        return doc

    def _generate_alerts(self, organization_id: str, docs: list[CompanyDocument]) -> list[CompanyDocumentAlert]:
        existing = self.alerts.list(organization_id, limit=1000)
        by_doc_type = {(a.document_id, a.tipo): a for a in existing}
        out = []
        for doc in docs:
            days = self._days_to_expiry(doc.validade)
            if doc.status in {'vencendo','vencido','pendente','inválido'}:
                tipo = 'vencimento' if doc.status in {'vencendo','vencido'} else 'pendencia'
                sev = 'critica' if doc.status in {'vencido','inválido'} or doc.criticidade == 'critica' else ('alta' if doc.status == 'vencendo' else 'media')
                msg = f'{doc.titulo}: {doc.status}' + (f' ({days} dias)' if days is not None else '')
                alert = by_doc_type.get((doc.id, tipo)) or CompanyDocumentAlert(organization_id=organization_id, document_id=doc.id, empresa_id=doc.empresa_id, empresa_nome=doc.empresa_nome or doc.cliente_nome, tipo=tipo, severidade=sev, mensagem=msg, dias_para_vencer=days)
                alert.severidade = sev; alert.mensagem = msg; alert.dias_para_vencer = days; alert.status = 'ativo'
                self.alerts.upsert(alert); out.append(alert)
                if sev in {'alta','critica'}: structured_log('api', 'documental_documento_critico', 'alerta', {'document_id': doc.id, 'status': doc.status, 'dias': days})
        return sorted(out, key=lambda a: {'critica': 0, 'alta': 1, 'media': 2, 'baixa': 3}.get(a.severidade, 9))

    def _score_empresa(self, docs: list[CompanyDocument]) -> int:
        if not docs: return 0
        return max(0, min(100, round(sum(d.score_documental for d in docs) / len(docs))))

    def _infer_required_types(self, text: str) -> list[str]:
        lower = (text or '').lower(); req = {'cartao_cnpj', 'certidao', 'contrato_social'}
        if 'balanço' in lower or 'balanco' in lower or 'índice' in lower or 'indice' in lower: req.update({'balanco', 'indices_contabeis'})
        if 'atestado' in lower or 'capacidade técnica' in lower or 'capacidade tecnica' in lower: req.add('atestado')
        if 'procuração' in lower or 'procuracao' in lower: req.add('procuracao')
        if 'alvará' in lower or 'alvara' in lower: req.add('alvara')
        if 'iso' in lower: req.add('iso')
        if 'trabalhista' in lower: req.add('documento_trabalhista')
        if 'fiscal' in lower: req.add('documento_fiscal')
        return [t for t in DOCUMENT_TYPES if t in req]

    def _days_to_expiry(self, value: str | None) -> int | None:
        if not value: return None
        try:
            d = datetime.fromisoformat(str(value).replace('Z', '+00:00')).date()
        except Exception:
            try: d = date.fromisoformat(str(value)[:10])
            except Exception: return None
        return (d - datetime.now(timezone.utc).date()).days

    def _safe_filename(self, filename: str) -> str:
        return re.sub(r'[^A-Za-z0-9À-ÿ._-]+', '-', Path(filename).name.strip() or 'documento')[:160]
