from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.schemas.fornecedor_full import FornecedorDashboardResponse, FornecedorRecord, FornecedorRecordCreate, FornecedorRecordUpdate
from app.services.audit_log import audit_event
from app.services.full_module_store import HybridFullModuleStore


class LiciFornecedorFullService:
    def __init__(self):
        self.store = HybridFullModuleStore('fornecedor_full', FornecedorRecord, '/root/lici-app/fornecedor_full', 'fornecedor_full_records')

    def info(self) -> dict[str, object]:
        return {'nome': 'LICI Fornecedor Full', 'status': 'ativo', 'sem_ia_livre': True, 'postgres_hibrido': True, 'fallback_json': True}

    def list(self, organization_id: str, tipo: str | None = None, limit: int = 200, offset: int = 0) -> list[FornecedorRecord]:
        return self.store.list(organization_id=organization_id or 'default-org', tipo=tipo, limit=limit, offset=offset)

    def create(self, payload: FornecedorRecordCreate, organization_id: str) -> FornecedorRecord:
        item = FornecedorRecord(**payload.model_dump(), organization_id=organization_id or 'default-org')
        item.risco_score = self._risk(item)
        item.margem_operacional = self._margin(item)
        saved = self.store.upsert(item)
        audit_event('fornecedor_full', f'{payload.tipo}_criado', 'ok', {'titulo': item.titulo, 'organization_id': item.organization_id}, item.id)
        return saved

    def update(self, record_id: str, payload: FornecedorRecordUpdate, organization_id: str) -> FornecedorRecord:
        item = self.store.get(record_id, organization_id=organization_id or 'default-org')
        if not item:
            if self.store.exists(record_id):
                audit_event('fornecedor_full', 'cross_org_bloqueado', 'erro', {'record_id': record_id, 'organization_id': organization_id}, record_id)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Registro pertence a outra organização')
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Registro não encontrado')
        data = item.model_dump()
        for key, value in payload.model_dump(exclude_unset=True).items():
            data[key] = value
        data['atualizado_em'] = datetime.now(timezone.utc)
        updated = FornecedorRecord(**data)
        updated.risco_score = self._risk(updated)
        updated.margem_operacional = self._margin(updated)
        saved = self.store.upsert(updated)
        audit_event('fornecedor_full', f'{saved.tipo}_atualizado', 'ok', {'status': saved.status}, saved.id)
        return saved

    def dashboard(self, organization_id: str) -> FornecedorDashboardResponse:
        items = self.list(organization_id)
        contratos = [i for i in items if i.tipo == 'contrato']
        financeiros = [i for i in items if i.tipo == 'financeiro']
        execucoes = [i for i in items if i.tipo == 'execucao']
        riscos = [i for i in items if i.tipo == 'risco']
        org_risk = defaultdict(list)
        for item in items:
            if item.orgao:
                org_risk[item.orgao].append(item.risco_score)
        orgaos_criticos = sorted([
            {'orgao': orgao, 'risco_medio': round(sum(vals) / len(vals), 1), 'eventos': len(vals)}
            for orgao, vals in org_risk.items() if vals
        ], key=lambda x: x['risco_medio'], reverse=True)[:8]
        margem_vals = [i.margem_operacional for i in items if i.margem_operacional]
        pendente = [i for i in financeiros if i.status in {'pendente', 'atrasado', 'em atraso', 'a receber'}]
        receita = sum(i.valor for i in financeiros if i.status not in {'cancelado', 'glosado'})
        atrasado = sum(i.valor for i in financeiros if i.status in {'atrasado', 'em atraso'})
        return FornecedorDashboardResponse(
            contratos_ativos=len([i for i in contratos if i.status in {'ativo', 'vigente', 'em execução'}]),
            pagamentos_pendentes=len(pendente),
            risco_contratual_medio=round(sum(i.risco_score for i in (riscos or items)) / max(len(riscos or items), 1), 1),
            margem_operacional_media=round(sum(margem_vals) / max(len(margem_vals), 1), 2),
            orgaos_criticos=orgaos_criticos,
            por_tipo=dict(Counter(i.tipo for i in items)),
            por_status=dict(Counter(i.status for i in items)),
            proximas_renovacoes=[i for i in contratos if i.status in {'ativo', 'vigente', 'renovação', 'renovacao'}][:8],
            pendencias_execucao=[i for i in execucoes if i.status in {'pendente', 'em atraso', 'ocorrência', 'ocorrencia'}][:8],
            financeiro={'receita_prevista': receita, 'valor_atrasado': atrasado, 'margem_media': round(sum(margem_vals) / max(len(margem_vals), 1), 2)},
        )

    def _risk(self, item: FornecedorRecord) -> int:
        text = f'{item.status} {item.prioridade} {item.observacoes} {item.payload}'.lower()
        score = 20
        if item.tipo == 'risco': score += 25
        for term in ['atraso', 'mau pagador', 'glosa', 'sanção', 'sancao', 'recorrente', 'pendente', 'fiscalização']:
            if term in text: score += 10
        if item.prioridade in {'alta', 'critica', 'crítica'}: score += 15
        return min(score, 100)

    def _margin(self, item: FornecedorRecord) -> float:
        payload = item.payload or {}
        receita = float(payload.get('receita', item.valor or 0) or 0)
        custo = float(payload.get('custo', 0) or 0)
        if receita <= 0: return 0
        return round(((receita - custo) / receita) * 100, 2)
