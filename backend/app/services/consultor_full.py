from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel

from app.schemas.consultor_full import (
    ConsultorFollowup,
    ConsultorFollowupCreate,
    ConsultorFollowupUpdate,
    ConsultorFullDashboardResponse,
    ConsultorFullRecord,
    ConsultorFullRecordCreate,
    ConsultorFullRecordUpdate,
    ConsultorLead,
    ConsultorLeadCreate,
    ConsultorLeadUpdate,
)
from app.services.audit_log import audit_event
from app.services.full_module_store import HybridFullModuleStore
from app.services.observability import structured_log

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

POSTGRES_ENV_FILE = Path('/root/lici-app/secrets/postgres.env')
PIPELINE_ETAPAS = ['Lead', 'Diagnóstico', 'Proposta', 'Negociação', 'Cliente', 'Operação', 'Recorrência']
CLIENTE_ETAPAS = {'Cliente', 'Operação', 'Recorrência'}
LEAD_STATUS_ENCERRADOS = {'perdido', 'ganho', 'arquivado'}
T = TypeVar('T', bound=BaseModel)


class ConsultorDeepStore:
    def __init__(self, module: str, model: type[T], path: str, table: str, kind: str):
        self.module = module
        self.model = model
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_json([])
        self.table = table
        self.kind = kind
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
        limit = max(1, min(int(limit or 200), 1000))
        offset = max(0, int(offset or 0))
        try:
            if self.available():
                self._ensure_table()
                with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
                    with conn.cursor() as cur:
                        where = ['organization_id = %s']
                        params: list[Any] = [organization_id]
                        for key in ('status', 'pipeline_etapa', 'lead_id', 'cliente_id'):
                            value = filters.get(key)
                            if value:
                                where.append(f'{key} = %s')
                                params.append(value)
                        sql = f"SELECT raw_payload FROM {self.table} WHERE " + ' AND '.join(where) + ' ORDER BY updated_at DESC LIMIT %s OFFSET %s'
                        params.extend([limit, offset])
                        cur.execute(sql, params)
                        return [self.model(**self._raw(row['raw_payload'])) for row in cur.fetchall()]
            audit_event(self.module, 'postgres_fallback_json', 'erro', {'operacao': f'list_{self.kind}', 'motivo': 'postgres_indisponivel'})
        except Exception as exc:
            audit_event(self.module, 'postgres_fallback_json', 'erro', {'operacao': f'list_{self.kind}', 'erro': str(exc)})
        items = [i for i in self._read_json() if (getattr(i, 'organization_id', None) or 'default-org') == organization_id]
        for key, value in filters.items():
            if value:
                items = [i for i in items if getattr(i, key, None) == value]
        return sorted(items, key=lambda item: getattr(item, 'atualizado_em', None) or getattr(item, 'criado_em', None), reverse=True)[offset:offset + limit]

    def get(self, record_id: str, organization_id: str | None = None) -> T | None:
        if self.available():
            try:
                self._ensure_table()
                with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
                    with conn.cursor() as cur:
                        if organization_id:
                            cur.execute(f'SELECT raw_payload FROM {self.table} WHERE id = %s AND organization_id = %s', (record_id, organization_id))
                        else:
                            cur.execute(f'SELECT raw_payload FROM {self.table} WHERE id = %s', (record_id,))
                        row = cur.fetchone()
                        if row:
                            return self.model(**self._raw(row['raw_payload']))
            except Exception as exc:
                audit_event(self.module, 'postgres_fallback_json', 'erro', {'operacao': f'get_{self.kind}', 'erro': str(exc)}, record_id)
        for item in self._read_json():
            if item.id == record_id and (not organization_id or (getattr(item, 'organization_id', None) or 'default-org') == organization_id):
                return item
        return None

    def exists(self, record_id: str) -> bool:
        return self.get(record_id, None) is not None

    def upsert(self, item: T) -> T:
        items = self._read_json()
        for idx, current in enumerate(items):
            if current.id == item.id:
                items[idx] = item
                break
        else:
            items.append(item)
        self._write_json([entry.model_dump() for entry in items])
        try:
            if self.available():
                self._ensure_table()
                data = item.model_dump()
                org_id = getattr(item, 'organization_id', 'default-org') or 'default-org'
                with psycopg.connect(self.dsn, connect_timeout=3) as conn:
                    with conn.transaction():
                        with conn.cursor() as cur:
                            cur.execute(
                                f'''
                                INSERT INTO {self.table} (id, organization_id, status, pipeline_etapa, lead_id, cliente_id, raw_payload, created_at, updated_at)
                                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                                ON CONFLICT (id) DO UPDATE SET
                                  organization_id = EXCLUDED.organization_id,
                                  status = EXCLUDED.status,
                                  pipeline_etapa = EXCLUDED.pipeline_etapa,
                                  lead_id = EXCLUDED.lead_id,
                                  cliente_id = EXCLUDED.cliente_id,
                                  raw_payload = EXCLUDED.raw_payload,
                                  updated_at = EXCLUDED.updated_at
                                ''',
                                (
                                    item.id,
                                    org_id,
                                    getattr(item, 'status', ''),
                                    getattr(item, 'pipeline_etapa', ''),
                                    getattr(item, 'lead_id', None),
                                    getattr(item, 'cliente_id', None),
                                    json.dumps(data, ensure_ascii=False, default=str),
                                    getattr(item, 'criado_em', None),
                                    getattr(item, 'atualizado_em', None),
                                ),
                            )
                audit_event(self.module, 'dual_write_postgres', 'ok', {'operacao': f'upsert_{self.kind}', 'tabela': self.table}, item.id)
            else:
                audit_event(self.module, 'dual_write_postgres', 'erro', {'operacao': f'upsert_{self.kind}', 'motivo': 'postgres_indisponivel'}, item.id)
        except Exception as exc:
            audit_event(self.module, 'dual_write_postgres', 'erro', {'operacao': f'upsert_{self.kind}', 'erro': str(exc)}, item.id)
        return item

    def _ensure_table(self) -> None:
        if self._table_ready:
            return
        if not psycopg or not self.dsn:
            raise RuntimeError('PostgreSQL indisponível')
        with psycopg.connect(self.dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.table} (
                        id TEXT PRIMARY KEY,
                        organization_id TEXT NOT NULL DEFAULT 'default-org',
                        status TEXT NOT NULL DEFAULT '',
                        pipeline_etapa TEXT NOT NULL DEFAULT '',
                        lead_id TEXT,
                        cliente_id TEXT,
                        raw_payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ,
                        updated_at TIMESTAMPTZ
                    )
                ''')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_org_status ON {self.table} (organization_id, status)')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_org_pipeline ON {self.table} (organization_id, pipeline_etapa)')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_org_updated ON {self.table} (organization_id, updated_at DESC)')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_lead_id ON {self.table} (lead_id)')
                cur.execute(f'CREATE INDEX IF NOT EXISTS idx_{self.table}_cliente_id ON {self.table} (cliente_id)')
            conn.commit()
        self._table_ready = True

    def _read_json(self) -> list[T]:
        try:
            raw = json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            raw = []
        return [self.model(**item) for item in raw]

    def _write_json(self, data: list[dict[str, Any]]) -> None:
        with NamedTemporaryFile('w', encoding='utf-8', dir=self.path.parent, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2, default=str)
            tmp.write('\n')
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.path)

    def _raw(self, raw: Any) -> dict[str, Any]:
        return json.loads(raw) if isinstance(raw, str) else dict(raw or {})

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding='utf-8').splitlines():
                if line.startswith('LICI_DATABASE_URL='):
                    return line.split('=', 1)[1].strip()
        except FileNotFoundError:
            return None
        return None


class LiciConsultorFullService:
    def __init__(self):
        self.store = HybridFullModuleStore('consultor_full', ConsultorFullRecord, '/root/lici-app/consultor_full', 'consultor_full_records')
        self.leads = ConsultorDeepStore('consultor_full', ConsultorLead, '/root/lici-app/consultor_full/leads.json', 'consultor_leads', 'lead')
        self.followups = ConsultorDeepStore('consultor_full', ConsultorFollowup, '/root/lici-app/consultor_full/followups.json', 'consultor_followups', 'followup')

    def info(self) -> dict[str, object]:
        return {'nome': 'LICI Consultor Full Profundo', 'status': 'ativo', 'fase': 'CRM e Carteira', 'sem_ia_livre': True, 'postgres_hibrido': True, 'fallback_json': True, 'tabelas': ['consultor_full_records', 'consultor_leads', 'consultor_followups']}

    def list(self, organization_id: str, tipo: str | None = None, limit: int = 200, offset: int = 0) -> list[ConsultorFullRecord]:
        return self.store.list(organization_id=organization_id or 'default-org', tipo=tipo, limit=limit, offset=offset)

    def list_leads(self, organization_id: str, status_value: str | None = None, pipeline_etapa: str | None = None, limit: int = 200, offset: int = 0) -> list[ConsultorLead]:
        return self.leads.list(organization_id or 'default-org', status=status_value, pipeline_etapa=pipeline_etapa, limit=limit, offset=offset)

    def list_followups(self, organization_id: str, lead_id: str | None = None, status_value: str | None = None, limit: int = 200, offset: int = 0) -> list[ConsultorFollowup]:
        return self.followups.list(organization_id or 'default-org', lead_id=lead_id, status=status_value, limit=limit, offset=offset)

    def create_lead(self, payload: ConsultorLeadCreate, organization_id: str) -> ConsultorLead:
        item = ConsultorLead(**payload.model_dump(), organization_id=organization_id or 'default-org')
        item.score_cliente = self._score_lead(item)
        item.historico_comercial.append({'evento': 'lead_criado', 'status': item.status, 'pipeline_etapa': item.pipeline_etapa, 'timestamp': datetime.now(timezone.utc).isoformat()})
        saved = self.leads.upsert(item)
        audit_event('consultor_full', 'lead_criado', 'ok', {'nome': item.nome, 'origem': item.origem, 'organization_id': item.organization_id}, item.id)
        structured_log('api', 'consultor_lead_criado', 'ok', {'id': item.id, 'organization_id': item.organization_id})
        return saved

    def update_lead(self, lead_id: str, payload: ConsultorLeadUpdate, organization_id: str) -> ConsultorLead:
        item = self.leads.get(lead_id, organization_id=organization_id or 'default-org')
        if not item:
            if self.leads.exists(lead_id):
                audit_event('consultor_full', 'cross_org_bloqueado', 'erro', {'lead_id': lead_id, 'organization_id': organization_id}, lead_id)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Lead pertence a outra organização')
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Lead não encontrado')
        old = {'status': item.status, 'pipeline_etapa': item.pipeline_etapa}
        data = item.model_dump()
        for key, value in payload.model_dump(exclude_unset=True).items():
            data[key] = value
        data['atualizado_em'] = datetime.now(timezone.utc)
        updated = ConsultorLead(**data)
        updated.score_cliente = self._score_lead(updated)
        updated.historico_comercial.append({'evento': 'lead_atualizado', 'antes': old, 'depois': {'status': updated.status, 'pipeline_etapa': updated.pipeline_etapa}, 'timestamp': datetime.now(timezone.utc).isoformat()})
        saved = self.leads.upsert(updated)
        audit_event('consultor_full', 'lead_atualizado', 'ok', {'status': saved.status, 'pipeline_etapa': saved.pipeline_etapa, 'score_cliente': saved.score_cliente}, saved.id)
        return saved

    def create_followup(self, payload: ConsultorFollowupCreate, organization_id: str) -> ConsultorFollowup:
        item = ConsultorFollowup(**payload.model_dump(), organization_id=organization_id or 'default-org')
        saved = self.followups.upsert(item)
        if item.lead_id:
            lead = self.leads.get(item.lead_id, organization_id=organization_id or 'default-org')
            if lead:
                lead.historico_comercial.append({'evento': 'followup_criado', 'titulo': item.titulo, 'status': item.status, 'timestamp': datetime.now(timezone.utc).isoformat()})
                lead.atualizado_em = datetime.now(timezone.utc)
                self.leads.upsert(lead)
        audit_event('consultor_full', 'followup_criado', 'ok', {'titulo': item.titulo, 'lead_id': item.lead_id, 'organization_id': item.organization_id}, item.id)
        return saved

    def update_followup(self, followup_id: str, payload: ConsultorFollowupUpdate, organization_id: str) -> ConsultorFollowup:
        item = self.followups.get(followup_id, organization_id=organization_id or 'default-org')
        if not item:
            if self.followups.exists(followup_id):
                audit_event('consultor_full', 'cross_org_bloqueado', 'erro', {'followup_id': followup_id, 'organization_id': organization_id}, followup_id)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Follow-up pertence a outra organização')
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Follow-up não encontrado')
        data = item.model_dump()
        for key, value in payload.model_dump(exclude_unset=True).items():
            data[key] = value
        data['atualizado_em'] = datetime.now(timezone.utc)
        saved = self.followups.upsert(ConsultorFollowup(**data))
        audit_event('consultor_full', 'followup_atualizado', 'ok', {'status': saved.status, 'resultado': saved.resultado}, saved.id)
        return saved

    def create(self, payload: ConsultorFullRecordCreate, organization_id: str) -> ConsultorFullRecord:
        item = ConsultorFullRecord(**payload.model_dump(), organization_id=organization_id or 'default-org')
        item.score = self._score(item)
        saved = self.store.upsert(item)
        audit_event('consultor_full', f'{payload.tipo}_criado', 'ok', {'titulo': item.titulo, 'organization_id': item.organization_id}, item.id)
        return saved

    def update(self, record_id: str, payload: ConsultorFullRecordUpdate, organization_id: str) -> ConsultorFullRecord:
        item = self.store.get(record_id, organization_id=organization_id or 'default-org')
        if not item:
            if self.store.exists(record_id):
                audit_event('consultor_full', 'cross_org_bloqueado', 'erro', {'record_id': record_id, 'organization_id': organization_id}, record_id)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Registro pertence a outra organização')
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Registro não encontrado')
        data = item.model_dump()
        for key, value in payload.model_dump(exclude_unset=True).items():
            data[key] = value
        data['atualizado_em'] = datetime.now(timezone.utc)
        updated = ConsultorFullRecord(**data)
        updated.score = self._score(updated)
        saved = self.store.upsert(updated)
        audit_event('consultor_full', f'{saved.tipo}_atualizado', 'ok', {'status': saved.status, 'etapa': saved.etapa}, saved.id)
        return saved

    def pipeline(self, organization_id: str) -> dict[str, Any]:
        leads = self.list_leads(organization_id, limit=1000)
        por_etapa = {stage: [] for stage in PIPELINE_ETAPAS}
        for lead in leads:
            por_etapa.setdefault(lead.pipeline_etapa, []).append(lead)
        return {
            'etapas': PIPELINE_ETAPAS,
            'colunas': {stage: por_etapa.get(stage, []) for stage in PIPELINE_ETAPAS},
            'metricas': self._conversion_metrics(leads),
        }

    def central_360(self, organization_id: str) -> list[dict[str, Any]]:
        return self._central_clientes(organization_id, self.list(organization_id, limit=1000), self.list_leads(organization_id, limit=1000), self.list_followups(organization_id, limit=1000))

    def dashboard(self, organization_id: str) -> ConsultorFullDashboardResponse:
        items = self.list(organization_id, limit=1000)
        leads_deep = self.list_leads(organization_id, limit=1000)
        followups = self.list_followups(organization_id, limit=1000)
        leads_records = [i for i in items if i.tipo == 'lead']
        tarefas = [i for i in items if i.tipo == 'tarefa']
        financeiros = [i for i in items if i.tipo == 'financeiro']
        carteira_records = [i for i in items if i.tipo == 'carteira']
        agenda = [i for i in items if i.tipo == 'agenda']
        receita = sum(i.valor for i in financeiros if i.status not in {'inadimplente', 'cancelado'}) + sum(l.ticket_medio + l.recorrencia for l in leads_deep if l.status == 'ganho')
        inad = sum(i.valor for i in financeiros if i.status == 'inadimplente')
        pipeline_counter = Counter({stage: 0 for stage in PIPELINE_ETAPAS})
        pipeline_counter.update(l.pipeline_etapa for l in leads_deep)
        legacy_pipeline = Counter((i.etapa or i.status or 'sem_etapa') for i in leads_records)
        carteira_counter = Counter(l.classificacao for l in leads_deep if l.pipeline_etapa in CLIENTE_ETAPAS or l.status == 'ganho')
        carteira_counter.update((i.payload or {}).get('classificacao', 'sem_classificacao') for i in carteira_records)
        pending_followups = [f for f in followups if f.status in {'pendente', 'aberta', 'em andamento'}]
        clientes_risco = len([l for l in leads_deep if l.risco_churn >= 60])
        return ConsultorFullDashboardResponse(
            leads_abertos=len([i for i in leads_records if i.status not in {'perdido', 'convertido', 'cancelado', 'ganho', 'arquivado'}]) + len([l for l in leads_deep if l.status not in LEAD_STATUS_ENCERRADOS]),
            leads_ativos=len([l for l in leads_deep if l.status not in LEAD_STATUS_ENCERRADOS]),
            conversao=self._conversion_metrics(leads_deep)['conversao_pct'],
            clientes_ativos=len({l.cliente_id or l.empresa or l.nome for l in leads_deep if l.status == 'ganho' or l.pipeline_etapa in CLIENTE_ETAPAS} | {i.cliente_id or i.cliente_nome for i in items if i.cliente_id or i.cliente_nome}),
            clientes_risco=clientes_risco,
            tarefas_pendentes=len([i for i in tarefas if i.status in {'pendente', 'aberta', 'em andamento'}]) + len(pending_followups),
            receita_prevista=receita,
            faturamento=receita,
            inadimplencia=inad,
            ticket_medio=round(receita / max(len([i for i in financeiros if i.valor]) + len([l for l in leads_deep if l.ticket_medio]), 1), 2),
            produtividade=self._produtividade(tarefas, followups),
            por_tipo=dict(Counter(i.tipo for i in items) | Counter({'lead_crm': len(leads_deep), 'followup': len(followups)})),
            pipeline=dict(legacy_pipeline),
            pipeline_comercial=dict(pipeline_counter),
            carteira=dict(carteira_counter),
            agenda_proxima=agenda[:8],
            tarefas=[i for i in tarefas if i.status in {'pendente', 'aberta', 'em andamento'}][:10],
            followups=pending_followups[:10],
            central_clientes=self._central_clientes(organization_id, items, leads_deep, followups)[:12],
        )

    def _score(self, item: ConsultorFullRecord) -> int:
        score = 35
        if item.valor >= 5000: score += 15
        if item.prioridade in {'alta', 'critica', 'crítica'}: score += 15
        if item.etapa in {'proposta', 'negociação', 'negociacao', 'cliente', 'operação', 'operacao', 'recorrência', 'recorrencia'}: score += 15
        if (item.payload or {}).get('classificacao') == 'A': score += 20
        if item.status in {'inadimplente', 'risco', 'atrasado'}: score -= 15
        return max(0, min(score, 100))

    def _score_lead(self, lead: ConsultorLead) -> int:
        score = 25
        if lead.classificacao == 'A': score += 25
        elif lead.classificacao == 'B': score += 15
        if lead.potencial >= 10000: score += 15
        if lead.ticket_medio >= 3000: score += 10
        if lead.recorrencia > 0: score += 10
        if lead.pipeline_etapa in {'Proposta', 'Negociação'}: score += 10
        if lead.pipeline_etapa in CLIENTE_ETAPAS or lead.status == 'ganho': score += 15
        score -= int((lead.risco_churn or 0) * 0.25)
        if lead.status in {'perdido', 'arquivado'}: score -= 25
        return max(0, min(score, 100))

    def _conversion_metrics(self, leads: list[ConsultorLead]) -> dict[str, Any]:
        ganhos = len([l for l in leads if l.status == 'ganho'])
        perdidos = len([l for l in leads if l.status == 'perdido'])
        ativos = len([l for l in leads if l.status not in LEAD_STATUS_ENCERRADOS])
        base = ganhos + perdidos
        return {'ganhos': ganhos, 'perdidos': perdidos, 'ativos': ativos, 'conversao_pct': round((ganhos / base) * 100, 2) if base else 0}

    def _produtividade(self, tarefas: list[ConsultorFullRecord], followups: list[ConsultorFollowup]) -> dict[str, Any]:
        concluidas = len([t for t in tarefas if t.status in {'concluida', 'concluído', 'feito'}]) + len([f for f in followups if f.status in {'concluido', 'concluído', 'feito'}])
        pendentes = len([t for t in tarefas if t.status in {'pendente', 'aberta', 'em andamento'}]) + len([f for f in followups if f.status in {'pendente', 'aberta', 'em andamento'}])
        por_responsavel = Counter([t.responsavel or 'sem_responsavel' for t in tarefas] + [f.responsavel or 'sem_responsavel' for f in followups])
        return {'concluidas': concluidas, 'pendentes': pendentes, 'por_responsavel': dict(por_responsavel)}

    def _central_clientes(self, organization_id: str, items: list[ConsultorFullRecord], leads: list[ConsultorLead], followups: list[ConsultorFollowup]) -> list[dict[str, Any]]:
        clientes = defaultdict(lambda: {'cliente_id': None, 'cliente_nome': '', 'faturamento': 0.0, 'risco': 0, 'historico': 0, 'timeline': [], 'tarefas': 0, 'pendencias': 0, 'score': 0, 'casos': 0, 'oportunidades': 0, 'pecas': 0, 'documentos': 0, 'concorrentes_relacionados': 0, 'orgaos_relacionados': 0, 'orgaos_prioritarios': []})
        for lead in leads:
            key = lead.cliente_id or lead.empresa or lead.nome
            c = clientes[key]
            c['cliente_id'] = lead.cliente_id
            c['cliente_nome'] = lead.empresa or lead.nome
            c['score'] = max(c['score'], lead.score_cliente)
            c['risco'] = max(c['risco'], lead.risco_churn)
            c['historico'] += len(lead.historico_comercial)
            c['timeline'].extend(lead.historico_comercial[-5:])
            c['faturamento'] += lead.ticket_medio + lead.recorrencia
            c['orgaos_prioritarios'] = sorted(set(c['orgaos_prioritarios']) | set(lead.orgaos_prioritarios))
        for item in items:
            key = item.cliente_id or item.cliente_nome or 'sem_cliente'
            if key == 'sem_cliente':
                continue
            c = clientes[key]
            c['cliente_id'] = item.cliente_id
            c['cliente_nome'] = item.cliente_nome or key
            c['score'] = max(c['score'], item.score)
            if item.tipo == 'financeiro': c['faturamento'] += item.valor
            if item.tipo == 'tarefa': c['tarefas'] += 1
            if item.tipo in {'portal', 'agenda'}: c['timeline'].append({'evento': item.tipo, 'titulo': item.titulo, 'timestamp': str(item.atualizado_em)})
            if item.prioridade in {'alta', 'critica', 'crítica'}: c['risco'] = max(c['risco'], 70)
        for followup in followups:
            key = followup.cliente_id or followup.cliente_nome or followup.lead_id or 'sem_cliente'
            if key == 'sem_cliente':
                continue
            c = clientes[key]
            c['cliente_id'] = followup.cliente_id
            c['cliente_nome'] = followup.cliente_nome or key
            c['pendencias'] += 1 if followup.status in {'pendente', 'aberta', 'em andamento'} else 0
            c['timeline'].append({'evento': 'followup', 'titulo': followup.titulo, 'status': followup.status, 'timestamp': str(followup.atualizado_em)})
        self._enriquecer_central_com_jsons(organization_id, clientes)
        return sorted(clientes.values(), key=lambda x: (x['score'], x['faturamento'], -x['risco']), reverse=True)

    def _enriquecer_central_com_jsons(self, organization_id: str, clientes: dict[str, dict[str, Any]]) -> None:
        fontes = [
            ('casos', Path('/root/lici-app/casos_vivos/casos.json'), ['cliente_nome', 'client_name', 'cliente'], 'casos'),
            ('oportunidades', Path('/root/lici-app/radar/oportunidades.json'), ['orgao', 'orgao_nome', 'orgao_name'], 'oportunidades'),
            ('documentos', Path('/root/lici-app/storage/documentos.json'), ['cliente_nome', 'orgao', 'orgao_nome'], 'documentos'),
            ('concorrentes', Path('/root/lici-app/concorrentes/concorrentes.json'), ['cliente_nome', 'orgao', 'orgao_nome'], 'concorrentes_relacionados'),
            ('orgaos', Path('/root/lici-app/orgaos/orgaos.json'), ['nome', 'orgao', 'orgao_nome'], 'orgaos_relacionados'),
        ]
        for _nome, path, keys, target in fontes:
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(data, list):
                    continue
                for row in data:
                    if row.get('organization_id') and row.get('organization_id') != organization_id:
                        continue
                    label = next((row.get(k) for k in keys if row.get(k)), None)
                    if not label:
                        continue
                    for c in clientes.values():
                        if label and c.get('cliente_nome') and (label.lower() in c['cliente_nome'].lower() or c['cliente_nome'].lower() in label.lower()):
                            c[target] += 1
            except Exception:
                continue
