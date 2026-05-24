from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.schemas.concorrente import (
    ConcorrenteAnaliseResponse,
    ConcorrenteCreate,
    ConcorrenteEvent,
    ConcorrenteEventCreate,
    ConcorrenteHistoricoResponse,
    ConcorrenteListResponse,
    ConcorrenteRecord,
    ConcorrenteUpdate,
)
from app.schemas.memory import MemoryCreate
from app.services.audit_log import audit_event
from app.services.case_store import HybridCaseStore
from app.services.concorrente_store import HybridConcorrenteStore
from app.services.memory_core_client import MemoryCoreClient
from app.services.orgao_store import HybridOrgaoStore
from app.services.radar_store import HybridRadarStore
from app.services.observability import structured_log


class LiciConcorrentesEngine:
    def __init__(self, store: HybridConcorrenteStore | None = None):
        self.store = store or HybridConcorrenteStore()
        self.memory = MemoryCoreClient()
        self.case_store = HybridCaseStore()
        self.orgao_store = HybridOrgaoStore()
        self.radar_store = HybridRadarStore()

    def info(self) -> dict[str, object]:
        return {
            'nome': 'LICI Concorrentes Engine',
            'status': 'ativo',
            'objetivo': 'Transformar inteligência de concorrentes em módulo operacional estratégico para licitações.',
            'endpoints': ['GET /concorrentes/engine','GET /concorrentes','POST /concorrentes/registrar','GET /concorrentes/{id}','POST /concorrentes/{id}/registrar-evento','GET /concorrentes/{id}/historico','GET /concorrentes/analise'],
            'persistencia': {'json': ['/root/lici-app/concorrentes/concorrentes.json','/root/lici-app/concorrentes/historico.json'], 'postgresql': ['competitors','competitor_events']},
            'integracoes': ['Case Engine','Órgãos','Radar','Memory Core','Decision Engine','Chat LICI','Audit Log','Observabilidade'],
            'eventos': ['participou','venceu','perdeu','inabilitado','recurso','impugnação','abandono','comportamento agressivo','preço muito baixo','padrão documental','vínculo com órgão','vínculo com caso'],
        }

    def list(self, organization_id: str | None = None) -> ConcorrenteListResponse:
        started = datetime.now(timezone.utc)
        concorrentes = self.store.list(organization_id=organization_id)
        structured_log('api', 'concorrentes_list', 'ok', {'total': len(concorrentes)})
        audit_event('concorrentes_engine', 'consulta_concorrentes', 'ok', {'total': len(concorrentes), 'inicio': started.isoformat()})
        return ConcorrenteListResponse(total=len(concorrentes), concorrentes=concorrentes)

    def get(self, concorrente_id: str, organization_id: str | None = None) -> ConcorrenteRecord:
        concorrente = self.store.get(concorrente_id, organization_id=organization_id)
        if concorrente is None:
            if organization_id and self.store.get(concorrente_id) is not None:
                audit_event('security', 'acesso_negado_cross_org', 'erro', {'recurso': 'concorrente', 'concorrente_id': concorrente_id, 'organization_id': organization_id}, concorrente_id)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Acesso negado: concorrente pertence a outra organização')
            audit_event('concorrentes_engine', 'concorrente_nao_encontrado', 'erro', {'concorrente_id': concorrente_id}, concorrente_id)
            raise HTTPException(status_code=404, detail='concorrente não encontrado')
        audit_event('concorrentes_engine', 'consulta_concorrente', 'ok', {'nome': concorrente.nome}, concorrente.id)
        return concorrente

    def registrar(self, payload: ConcorrenteCreate, organization_id: str | None = None) -> ConcorrenteRecord:
        if organization_id and not payload.organization_id:
            payload = payload.model_copy(update={"organization_id": organization_id})
        existing = self.store.find_by_nome_cnpj(payload.nome, payload.cnpj)
        if existing and organization_id and (existing.organization_id or "default-org") != organization_id:
            existing = None
        if existing:
            concorrente = self._merge(existing, payload)
            action = 'atualizacao_concorrente'
        else:
            concorrente = ConcorrenteRecord(**payload.model_dump())
            action = 'registro_concorrente'
        concorrente.atualizado_em = self._now()
        concorrente = self._recalcular_por_contexto(concorrente)
        saved = self.store.upsert(concorrente)
        self._registrar_memoria_concorrente(saved, action)
        structured_log('api', 'concorrente_saved', 'ok', {'id': saved.id, 'nome': saved.nome, 'acao': action})
        audit_event('concorrentes_engine', action, 'ok', {'nome': saved.nome, 'cnpj': saved.cnpj, 'risco': saved.risco_operacional, 'score_risco': saved.score_risco}, saved.id)
        return saved

    def atualizar(self, concorrente_id: str, payload: ConcorrenteUpdate, organization_id: str | None = None) -> ConcorrenteRecord:
        concorrente = self.get(concorrente_id, organization_id=organization_id)
        data = concorrente.model_dump()
        for key, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                data[key] = {**data.get(key, {}), **value} if key == 'metadata' else value
        data['atualizado_em'] = self._now()
        updated = self._recalcular_por_contexto(ConcorrenteRecord(**data))
        saved = self.store.upsert(updated)
        audit_event('concorrentes_engine', 'atualizacao_concorrente_manual', 'ok', {'nome': saved.nome, 'organization_id': saved.organization_id}, saved.id)
        return saved

    def arquivar(self, concorrente_id: str, organization_id: str | None = None) -> ConcorrenteRecord:
        concorrente = self.get(concorrente_id, organization_id=organization_id)
        data = concorrente.model_dump()
        metadata = dict(data.get('metadata') or {})
        metadata.update({'arquivado': True, 'arquivado_em': self._now()})
        data['metadata'] = metadata
        data['atualizado_em'] = self._now()
        saved = self.store.upsert(ConcorrenteRecord(**data))
        audit_event('concorrentes_engine', 'arquivamento_concorrente', 'ok', {'nome': saved.nome}, saved.id)
        return saved

    def registrar_evento(self, concorrente_id: str, payload: ConcorrenteEventCreate, organization_id: str | None = None) -> ConcorrenteEvent:
        concorrente = self.get(concorrente_id, organization_id=organization_id)
        if organization_id and not payload.organization_id:
            payload = payload.model_copy(update={"organization_id": organization_id})
        event = ConcorrenteEvent(concorrente_id=concorrente_id, **payload.model_dump())
        saved_event = self.store.add_event(event)
        updated = self._aplicar_evento(concorrente, saved_event)
        updated.atualizado_em = self._now()
        self.store.upsert(updated)
        self._registrar_memoria_evento(updated, saved_event)
        structured_log('api', 'concorrente_event_saved', 'ok', {'concorrente_id': concorrente_id, 'tipo': saved_event.tipo})
        audit_event('concorrentes_engine', 'registro_evento_concorrente', 'ok', {'concorrente': updated.nome, 'tipo': saved_event.tipo, 'orgao': saved_event.orgao, 'caso_id': saved_event.caso_id}, updated.id)
        return saved_event

    def historico(self, concorrente_id: str, organization_id: str | None = None) -> ConcorrenteHistoricoResponse:
        self.get(concorrente_id, organization_id=organization_id)
        eventos = self.store.history(concorrente_id)
        audit_event('concorrentes_engine', 'consulta_historico_concorrente', 'ok', {'concorrente_id': concorrente_id, 'total': len(eventos)}, concorrente_id)
        return ConcorrenteHistoricoResponse(concorrente_id=concorrente_id, total=len(eventos), eventos=eventos)

    def analise(self, organization_id: str | None = None) -> ConcorrenteAnaliseResponse:
        concorrentes = self.store.list(organization_id=organization_id)
        eventos = self.store.events()
        by_comp = {c.id: c for c in concorrentes}
        orgaos = Counter(e.orgao for e in eventos if e.orgao)
        tipos = Counter(e.tipo for e in eventos if e.tipo)
        padroes_preco = Counter()
        for e in eventos:
            if e.tipo == 'preço muito baixo':
                padroes_preco['preço muito baixo'] += 1
            if e.valor_proposta is not None:
                padroes_preco['propostas com valor registrado'] += 1
        ranking = sorted(concorrentes, key=lambda c: (c.frequencia, c.vitorias, c.score_competitividade), reverse=True)[:10]
        risco_dist = Counter(c.risco_operacional for c in concorrentes)
        dashboard = {
            'ranking_concorrentes': [{'id': c.id, 'nome': c.nome, 'frequencia': c.frequencia, 'taxa_vitoria': self._win_rate(c), 'risco': c.risco_operacional, 'score_risco': c.score_risco, 'orgaos_relacionados': c.orgaos_relacionados[:5]} for c in ranking],
            'risco': [{'valor': k, 'total': v} for k, v in risco_dist.most_common()],
            'frequencia_total': sum(c.frequencia for c in concorrentes),
            'taxa_vitoria_media': round(sum(self._win_rate(c) for c in concorrentes) / len(concorrentes), 2) if concorrentes else 0,
        }
        response = ConcorrenteAnaliseResponse(
            total_concorrentes=len(concorrentes),
            total_eventos=len(eventos),
            ranking_concorrentes=dashboard['ranking_concorrentes'],
            orgaos_mais_disputados=[{'valor': k, 'total': v} for k, v in orgaos.most_common(10)],
            padroes_risco=[{'valor': k, 'total': v} for k, v in tipos.most_common(10)],
            padroes_preco=[{'valor': k, 'total': v} for k, v in padroes_preco.most_common(10)],
            risco_operacional={'distribuicao': dashboard['risco'], 'alto_ou_critico': sum(1 for c in concorrentes if c.risco_operacional in {'alto','crítico'})},
            dashboard=dashboard,
        )
        audit_event('concorrentes_engine', 'analise_concorrentes', 'ok', {'total_concorrentes': len(concorrentes), 'total_eventos': len(eventos)})
        structured_log('api', 'concorrentes_analysis', 'ok', {'total_concorrentes': len(concorrentes), 'total_eventos': len(eventos)})
        return response

    def _merge(self, current: ConcorrenteRecord, payload: ConcorrenteCreate) -> ConcorrenteRecord:
        data = current.model_dump()
        incoming = payload.model_dump()
        for key, value in incoming.items():
            if isinstance(value, list):
                data[key] = self._merge_list(data.get(key, []), value)
            elif isinstance(value, dict):
                data[key] = {**data.get(key, {}), **value}
            elif key in {'frequencia', 'vitorias', 'derrotas', 'inabilitacoes', 'recursos', 'impugnacoes'} and value == 0 and data.get(key, 0) > 0:
                continue
            elif value not in (None, '', 'desconhecido'):
                data[key] = value
        return ConcorrenteRecord(**data)

    def _aplicar_evento(self, c: ConcorrenteRecord, e: ConcorrenteEvent) -> ConcorrenteRecord:
        c.frequencia += 1 if e.tipo in {'participou','venceu','perdeu','inabilitado'} else 0
        if e.tipo == 'venceu':
            c.vitorias += 1; c.score_competitividade = min(100, c.score_competitividade + 8)
        elif e.tipo == 'perdeu':
            c.derrotas += 1; c.score_competitividade = max(0, c.score_competitividade - 2)
        elif e.tipo == 'inabilitado':
            c.inabilitacoes += 1; c.score_risco = min(100, c.score_risco + 8); c.risco_operacional = self._worse_risk(c.risco_operacional, 'alto')
        elif e.tipo == 'recurso':
            c.recursos += 1; c.score_risco = min(100, c.score_risco + 4)
        elif e.tipo == 'impugnação':
            c.impugnacoes += 1; c.score_risco = min(100, c.score_risco + 3)
        elif e.tipo == 'abandono':
            c.score_risco = min(100, c.score_risco + 6); c.risco_operacional = self._worse_risk(c.risco_operacional, 'médio')
        elif e.tipo == 'comportamento agressivo':
            c.score_risco = min(100, c.score_risco + 10); c.risco_operacional = self._worse_risk(c.risco_operacional, 'alto')
        elif e.tipo == 'preço muito baixo':
            c.padroes_preco = self._merge_list(c.padroes_preco, [e.descricao]); c.score_competitividade = min(100, c.score_competitividade + 5); c.score_risco = min(100, c.score_risco + 5)
        elif e.tipo == 'padrão documental':
            c.padroes_documentais = self._merge_list(c.padroes_documentais, [e.descricao])
        if e.orgao or e.tipo == 'vínculo com órgão':
            c.orgaos_relacionados = self._merge_list(c.orgaos_relacionados, [e.orgao or e.descricao])
        if e.caso_id or e.tipo == 'vínculo com caso':
            c.casos_relacionados = self._merge_list(c.casos_relacionados, [e.caso_id or e.descricao])
        return c

    def _recalcular_por_contexto(self, c: ConcorrenteRecord) -> ConcorrenteRecord:
        casos_ids = set(c.casos_relacionados)
        for case in self.case_store.list(organization_id=c.organization_id or "default-org"):
            hay = ' '.join([getattr(case, 'cliente', ''), getattr(case, 'orgao', ''), getattr(case, 'objeto', ''), str(getattr(case, 'metadata', ''))]).casefold()
            if c.nome.casefold() in hay:
                casos_ids.add(case.id)
        if casos_ids:
            c.casos_relacionados = self._merge_list(c.casos_relacionados, list(casos_ids))
        if c.inabilitacoes >= 2 or c.score_risco >= 75:
            c.risco_operacional = self._worse_risk(c.risco_operacional, 'alto')
        return c

    def _registrar_memoria_concorrente(self, c: ConcorrenteRecord, action: str) -> None:
        self.memory.registrar(MemoryCreate(tipo='concorrente', titulo=f'Concorrente: {c.nome}', descricao=f'Concorrente {c.nome} registrado no Concorrentes Engine.', contexto=f'CNPJ: {c.cnpj or "não informado"}; segmento: {c.segmento}; UF: {c.uf}; risco: {c.risco_operacional}.', estrategia=c.observacoes_estrategicas or 'Monitorar frequência, preço, comportamento e falhas documentais para usar estrategicamente em disputas.', aprendizado='Concorrente deve alimentar análise de risco, ataque lícito, decisão e preparação de habilitação/proposta.', uso_futuro='Consultar antes de disputa, recurso, contrarrazões, estratégia de preço e análise de risco competitivo.', tags=['concorrentes-engine', action, c.nome, c.uf], fonte='concorrentes_engine', confianca=0.75))

    def _registrar_memoria_evento(self, c: ConcorrenteRecord, e: ConcorrenteEvent) -> None:
        self.memory.registrar(MemoryCreate(tipo='concorrente', titulo=f'{c.nome}: {e.tipo}', descricao=e.descricao, contexto=f'Concorrente: {c.nome}; evento: {e.tipo}; órgão: {e.orgao or "não informado"}; caso_id: {e.caso_id or "não informado"}.', estrategia=e.impacto or 'Usar evento para calibrar risco, preço, recurso, impugnação e ataque lícito a falhas do concorrente.', aprendizado='Eventos de concorrentes aumentam inteligência competitiva reutilizável.', uso_futuro='Reutilizar em editais futuros, recursos, contrarrazões e análise de participação.', tags=['concorrentes-engine', str(e.tipo), c.nome, e.orgao], fonte='concorrentes_engine', confianca=0.8))

    def _win_rate(self, c: ConcorrenteRecord) -> float:
        total = c.vitorias + c.derrotas + c.inabilitacoes
        return round((c.vitorias / total) * 100, 2) if total else 0

    def _merge_list(self, left: list[str], right: list[str]) -> list[str]:
        out, seen = [], set()
        for item in left + right:
            item = str(item or '').strip()
            if not item or item in seen:
                continue
            seen.add(item); out.append(item)
        return out

    def _worse_risk(self, current: str, candidate: str) -> str:
        order = {'desconhecido': 0, 'baixo': 1, 'médio': 2, 'alto': 3, 'crítico': 4}
        return candidate if order.get(candidate, 0) > order.get(current, 0) else current

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
