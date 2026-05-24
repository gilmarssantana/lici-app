from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.company_document import CompanyChecklistRequest
from app.schemas.ia_assistiva import (
    AssistiveFeedbackRequest,
    AssistiveRequest,
    AssistiveResponse,
    AssistiveSource,
    AssistiveSuggestion,
    AssistiveTelemetryRecord,
    AssistiveTelemetrySummary,
)
from app.services.alert_store import HybridAlertStore
from app.services.audit_log import audit_event
from app.services.case_store import HybridCaseStore
from app.services.company_document import LiciCompanyDocumentService
from app.services.concorrente_store import HybridConcorrenteStore
from app.services.consultor_full import LiciConsultorFullService
from app.services.dashboard import LiciDashboardService
from app.services.memory_store import HybridMemoryStore
from app.services.observability import structured_log
from app.services.orgao_store import HybridOrgaoStore

ROOT = Path('/root/lici-app/ia_assistiva')
RESPONSES = ROOT / 'respostas.json'
TELEMETRY = ROOT / 'telemetria.json'


class LiciAssistiveAIService:
    """IA assistiva contextual: determinística/supervisionada, sem execução automática."""

    def __init__(self):
        ROOT.mkdir(parents=True, exist_ok=True)
        for path in (RESPONSES, TELEMETRY):
            if not path.exists():
                self._write_json(path, [])
        self.cases = HybridCaseStore()
        self.memory = HybridMemoryStore(settings.memory_root)
        self.docs = LiciCompanyDocumentService()
        self.concorrentes = HybridConcorrenteStore()
        self.orgaos = HybridOrgaoStore()
        self.dashboard = LiciDashboardService()
        self.alerts = HybridAlertStore()
        self.consultor = LiciConsultorFullService()

    def info(self) -> dict[str, Any]:
        return {
            'nome': 'LICI IA Assistiva Contextual',
            'fase': 'Fase 1',
            'status': 'ativo',
            'modo': 'assistivo_contextual_supervisionado',
            'sem_ia_autonoma': True,
            'execucao_automatica': False,
            'fontes_contextuais': ['casos','memoria_viva','clientes','documentos_empresariais','checklist','concorrentes','orgaos','dashboard','alertas','tarefas','pipeline_consultivo'],
            'endpoints': ['GET /ia-assistiva/engine','POST /ia-assistiva/responder','POST /ia-assistiva/feedback','GET /ia-assistiva/telemetria'],
            'telemetria': 'ativa',
        }

    def responder(self, payload: AssistiveRequest, user: dict[str, Any]) -> AssistiveResponse:
        org = self._org(user)
        fontes: list[AssistiveSource] = []
        contexto = self._contexto(payload, org, fontes)
        resumo = self._resumo(payload, contexto)
        explicacoes = self._explicacoes(payload, contexto)
        sugestoes = self._sugestoes(payload, contexto)
        confianca = self._confianca(contexto, fontes)
        resposta = self._montar_resposta(payload, resumo, explicacoes, sugestoes, fontes, confianca)
        out = AssistiveResponse(
            tipo=payload.tipo,
            foco=payload.foco,
            pergunta=payload.pergunta,
            resposta=resposta,
            resumo=resumo,
            explicacoes=explicacoes,
            sugestoes=sugestoes,
            fontes=fontes,
            dados_contexto=contexto if payload.incluir_dados else {},
            confianca=confianca,
        )
        self._append_response(out, org, user)
        audit_event('ia_assistiva', 'resposta_contextual', 'ok', {'tipo': payload.tipo, 'foco': payload.foco, 'confianca': confianca, 'fontes': [f.modulo for f in fontes]}, out.id)
        structured_log('api', 'ia_assistiva_resposta', 'ok', {'id': out.id, 'tipo': payload.tipo, 'foco': payload.foco, 'confianca': confianca, 'organization_id': org})
        return out

    def feedback(self, payload: AssistiveFeedbackRequest, user: dict[str, Any]) -> AssistiveTelemetrySummary:
        org = self._org(user)
        response = self._response_for_org(payload.resposta_id, org)
        records = self._read_json(TELEMETRY)
        records.append(AssistiveTelemetryRecord(
            organization_id=org,
            resposta_id=payload.resposta_id,
            tipo=response.get('tipo') or '',
            foco=response.get('foco') or '',
            confianca=float(response.get('confianca') or 0),
            feedback=payload.feedback,
            comentario=payload.comentario,
            usuario_id=user.get('id'),
        ).model_dump(mode='json'))
        self._write_json(TELEMETRY, records)
        audit_event('ia_assistiva', f'sugestao_{payload.feedback}', 'ok', {'resposta_id': payload.resposta_id}, payload.resposta_id)
        structured_log('api', 'ia_assistiva_feedback', 'ok', {'resposta_id': payload.resposta_id, 'feedback': payload.feedback, 'organization_id': org})
        return self.telemetria(org)

    def telemetria(self, organization_id: str) -> AssistiveTelemetrySummary:
        responses = [r for r in self._read_json(RESPONSES) if (r.get('organization_id') or 'default-org') == organization_id]
        feedbacks = [r for r in self._read_json(TELEMETRY) if (r.get('organization_id') or 'default-org') == organization_id]
        confs = [float(r.get('confianca') or 0) for r in responses]
        return AssistiveTelemetrySummary(
            total_respostas=len(responses),
            sugestoes_aceitas=sum(1 for r in feedbacks if r.get('feedback') == 'aceita'),
            sugestoes_ignoradas=sum(1 for r in feedbacks if r.get('feedback') == 'ignorada'),
            respostas_uteis=sum(1 for r in feedbacks if r.get('feedback') == 'util'),
            respostas_insuficientes=sum(1 for r in feedbacks if r.get('feedback') == 'insuficiente'),
            confianca_media=round(sum(confs) / max(len(confs), 1), 2),
            por_foco=dict(Counter(str(r.get('foco') or 'operacional') for r in responses)),
        )

    def _contexto(self, p: AssistiveRequest, org: str, fontes: list[AssistiveSource]) -> dict[str, Any]:
        termo = p.termo or p.pergunta or p.cliente_nome or p.empresa_nome or ''
        ctx: dict[str, Any] = {}
        cases = self._match(self.cases.list(organization_id=org), termo, ['id','cliente','orgao','objeto','fase_atual','status','riscos','oportunidades'])
        if p.caso_id: cases = [c for c in cases if getattr(c, 'id', '') == p.caso_id]
        ctx['casos'] = [self._dump(c) for c in cases[:5]]; fontes.append(self._source('Case Engine','caso',ctx['casos']))
        mem = self.memory.search(termo, organization_id=org)[:5] if termo else self.memory.list(organization_id=org)[:5]
        ctx['memoria_viva'] = [self._dump(m) for m in mem]; fontes.append(self._source('Memory Core','memoria',ctx['memoria_viva']))
        docs = self.docs.list_documents(org, limit=1000)
        if p.empresa_id: docs = [d for d in docs if d.empresa_id == p.empresa_id or d.cliente_id == p.empresa_id]
        if p.empresa_nome or p.cliente_nome:
            nome = (p.empresa_nome or p.cliente_nome).lower(); docs = [d for d in docs if nome in (d.empresa_nome or d.cliente_nome or '').lower()]
        docs_m = self._match(docs, termo, ['titulo','empresa_nome','cliente_nome','tipo_documental','status','tags','observacoes']) if termo else docs
        ctx['documentos'] = [self._dump(d) for d in docs_m[:20]]; fontes.append(self._source('Documental 360','documento',ctx['documentos']))
        if p.empresa_nome or p.empresa_id or p.cliente_nome:
            dossie = self.docs.dossier(org, empresa_id=p.empresa_id, empresa_nome=p.empresa_nome or p.cliente_nome).model_dump(mode='json')
            ctx['dossie'] = dossie; fontes.append(AssistiveSource(modulo='Documental 360', tipo='dossie', total=1, ids=[]))
        if p.edital_texto:
            checklist = self.docs.checklist(org, CompanyChecklistRequest(empresa_id=p.empresa_id, empresa_nome=p.empresa_nome or p.cliente_nome, edital_texto=p.edital_texto)).model_dump(mode='json')
            ctx['checklist'] = checklist; fontes.append(AssistiveSource(modulo='Documental 360', tipo='checklist', total=1, ids=[]))
        concorr = self._match(self.concorrentes.list(organization_id=org), termo, ['id','nome','cnpj','segmento','observacoes_estrategicas','risco_operacional','padroes_documentais','padroes_preco'])
        ctx['concorrentes'] = [self._dump(c) for c in concorr[:5]]; fontes.append(self._source('Concorrentes','concorrente',ctx['concorrentes']))
        orgaos = self._match(self.orgaos.list(organization_id=org), termo, ['id','nome','cnpj','uf','perfil','observacoes'])
        ctx['orgaos'] = [self._dump(o) for o in orgaos[:5]]; fontes.append(self._source('Órgãos','orgao',ctx['orgaos']))
        try:
            ctx['dashboard'] = self.dashboard.resumo(organization_id=org)
            org_alerts = self._filter_alerts_by_org(self.alerts.list_alerts(), org)
            ctx['dashboard'].setdefault('totais', {})['alertas'] = len(org_alerts)
            ctx['dashboard'].setdefault('totais', {})['alertas_nao_lidos'] = sum(1 for a in org_alerts if not getattr(a, 'lido', False))
        except Exception as exc: fontes.append(AssistiveSource(modulo='Dashboard', tipo='erro', status='erro', detalhe=str(exc)))
        try: ctx['alertas'] = [self._dump(a) for a in self._filter_alerts_by_org(self.alerts.list_alerts(), org)[:20]]
        except Exception as exc: fontes.append(AssistiveSource(modulo='Alertas', tipo='erro', status='erro', detalhe=str(exc)))
        leads = self.consultor.list_leads(org, limit=50); followups = self.consultor.list_followups(org, limit=50)
        ctx['pipeline_consultivo'] = {'leads': [self._dump(i) for i in leads[:10]], 'followups': [self._dump(i) for i in followups[:10]]}
        fontes.append(AssistiveSource(modulo='Consultor Full', tipo='pipeline_tarefas', total=len(leads)+len(followups), ids=[getattr(i,'id','') for i in (leads[:3]+followups[:3])]))
        return ctx

    def _resumo(self, p: AssistiveRequest, ctx: dict[str, Any]) -> list[str]:
        out: list[str] = []
        if p.foco == 'cliente':
            leads = ctx.get('pipeline_consultivo', {}).get('leads', [])
            out.append(f"Cliente/empresa com {len(ctx.get('documentos', []))} documento(s) contextual(is), {len(ctx.get('casos', []))} caso(s) e {len(leads)} lead(s) no pipeline consultivo.")
        elif p.foco == 'caso':
            for c in ctx.get('casos', [])[:3]: out.append(f"Caso {c.get('id')}: {c.get('objeto') or c.get('cliente')} — fase {c.get('fase_atual')}, status {c.get('status')}.")
        elif p.foco == 'edital':
            chk = ctx.get('checklist'); out.append(f"Edital confrontado com checklist: risco {chk.get('risco_inabilitacao')}, faltantes {len(chk.get('faltantes', []))}." if chk else 'Sem texto de edital suficiente para checklist documental.')
        elif p.foco == 'concorrencial':
            out.append(f"Foram encontrados {len(ctx.get('concorrentes', []))} concorrente(s) relacionados e {len(ctx.get('orgaos', []))} órgão(s) potencialmente conectados.")
        elif p.foco == 'documental':
            d = ctx.get('dossie'); out.append(f"Dossiê: score {d.get('score_documental')}, aptidão {d.get('aptidao_licitatoria')}, pendências {d.get('pendencias')}, riscos {d.get('riscos')}." if d else f"Documental: {len(ctx.get('documentos', []))} documento(s) localizado(s).")
        else:
            dash = ctx.get('dashboard', {}).get('totais', {})
            out.append(f"Operação: {dash.get('casos_vivos',0)} caso(s) vivo(s), {dash.get('alertas_nao_lidos',0)} alerta(s) não lido(s), {dash.get('oportunidades_radar',0)} oportunidade(s) no Radar.")
        return out

    def _explicacoes(self, p: AssistiveRequest, ctx: dict[str, Any]) -> list[str]:
        d = ctx.get('dossie') or {}
        chk = ctx.get('checklist') or {}
        docs = ctx.get('documentos') or []
        out: list[str] = []
        if p.foco in {'risco','pendencia','inaptidao_documental','documental','score'}:
            if d:
                out.append(f"O score documental decorre da média dos documentos válidos, vencendo, vencidos, pendentes e inválidos. Score atual: {d.get('score_documental')}.")
                if d.get('pendencias'): out.append('Há pendências documentais; isso aumenta risco de inabilitação se o edital exigir esses documentos.')
                if d.get('riscos'): out.append('Há documentos vencidos/vencendo ou com risco elevado; regularizar antes da habilitação.')
            criticos = [x for x in docs if x.get('status') in {'vencido','vencendo','pendente','inválido'} or int(x.get('risco_documental') or 0) >= 60]
            if criticos: out.append('Principais pontos críticos: ' + '; '.join(f"{x.get('titulo')} ({x.get('status')})" for x in criticos[:5]))
        if p.foco in {'decisao','edital'} and chk:
            out.append(f"A decisão operacional deve considerar o checklist: faltantes {chk.get('faltantes', [])}, vencidos {chk.get('vencidos', [])}, risco {chk.get('risco_inabilitacao')}.")
        if p.foco == 'concorrencial' and ctx.get('concorrentes'):
            out.append('Risco concorrencial deve observar padrões documentais, preço, órgãos recorrentes e histórico de inabilitação/recurso dos concorrentes encontrados.')
        if not out: out.append('A explicação foi limitada ao contexto interno disponível; sem fonte interna, a LICI não inventa dado.')
        return out

    def _sugestoes(self, p: AssistiveRequest, ctx: dict[str, Any]) -> list[AssistiveSuggestion]:
        suggestions: list[AssistiveSuggestion] = []
        d = ctx.get('dossie') or {}; chk = ctx.get('checklist') or {}
        if chk.get('faltantes') or chk.get('vencidos'):
            suggestions.append(AssistiveSuggestion(tipo='regularizacao', titulo='Regularizar documentos do checklist', descricao='Anexar/regularizar: ' + ', '.join((chk.get('faltantes') or []) + (chk.get('vencidos') or [])), prioridade='alta', motivo='Checklist indicou risco de inabilitação.'))
        if d.get('aptidao_licitatoria') in {'atenção','risco de inabilitação'}:
            suggestions.append(AssistiveSuggestion(tipo='prioridade', titulo='Priorizar saneamento documental', descricao='Atacar pendências e vencimentos antes de avançar para disputa/habilitação.', prioridade='alta', motivo=f"Aptidão documental: {d.get('aptidao_licitatoria')}"))
        followups = ctx.get('pipeline_consultivo', {}).get('followups', [])
        pend = [f for f in followups if f.get('status') in {'pendente','atrasado','aberto'}]
        if pend:
            suggestions.append(AssistiveSuggestion(tipo='follow_up', titulo='Revisar follow-ups pendentes', descricao=f"Há {len(pend)} follow-up(s) pendente(s) no pipeline consultivo.", prioridade='media', motivo='Pipeline consultivo possui tarefas abertas.'))
        if ctx.get('casos'):
            suggestions.append(AssistiveSuggestion(tipo='proxima_acao', titulo='Validar próximo ato do caso', descricao='Conferir fase atual, prazo e risco documental/concorrencial antes da próxima movimentação.', prioridade='media', motivo='Há caso(s) relacionado(s) no contexto.'))
        if not suggestions:
            suggestions.append(AssistiveSuggestion(tipo='sugestao_operacional', titulo='Consolidar dados antes de agir', descricao='Sem risco crítico identificado; revisar fontes internas e validar manualmente antes de qualquer execução.', prioridade='baixa', motivo='Sugestão assistiva, sem execução automática.'))
        return suggestions[:5]

    def _montar_resposta(self, p: AssistiveRequest, resumo: list[str], explicacoes: list[str], sugestoes: list[AssistiveSuggestion], fontes: list[AssistiveSource], confianca: float) -> str:
        parts = [f"IA Assistiva Contextual — {p.tipo}/{p.foco}.", f"Confiança: {round(confianca*100)}%. Modo supervisionado: não executo ações automaticamente."]
        if resumo: parts.append('Resumo:\n' + '\n'.join(f'- {x}' for x in resumo))
        if explicacoes: parts.append('Explicação:\n' + '\n'.join(f'- {x}' for x in explicacoes))
        if sugestoes: parts.append('Sugestões supervisionadas:\n' + '\n'.join(f'- [{s.prioridade}] {s.titulo}: {s.descricao}' for s in sugestoes))
        ok_sources = [f for f in fontes if f.status == 'ok' and f.total]
        parts.append('Fontes internas: ' + (', '.join(f'{f.modulo} ({f.total})' for f in ok_sources[:8]) or 'nenhuma fonte com dado suficiente'))
        return '\n\n'.join(parts)

    def _append_response(self, out: AssistiveResponse, org: str, user: dict[str, Any]) -> None:
        data = self._read_json(RESPONSES)
        data.append({**out.model_dump(mode='json'), 'organization_id': org, 'usuario_id': user.get('id')})
        self._write_json(RESPONSES, data)

    def _response_for_org(self, resposta_id: str, org: str) -> dict[str, Any]:
        for response in self._read_json(RESPONSES):
            if response.get('id') == resposta_id and (response.get('organization_id') or 'default-org') == org:
                return response
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Resposta assistiva não encontrada nesta organização')

    def _filter_alerts_by_org(self, alerts: list[Any], org: str) -> list[Any]:
        out = []
        for alert in alerts:
            data = self._dump(alert)
            metadata = data.get('metadata') or {}
            alert_org = metadata.get('organization_id') or data.get('organization_id') or 'default-org'
            if alert_org == org:
                out.append(alert)
        return out

    def _match(self, items: list[Any], term: str, fields: list[str]) -> list[Any]:
        terms = [t.casefold() for t in re.findall(r'[\wÀ-ÿ]{3,}', term or '') if t.casefold() not in {'resumo','explique','sobre','para','com','uma','documental','operacional'}]
        if not terms: return items[:20]
        out = []
        for item in items:
            data = self._dump(item); hay = ' '.join(self._stringify(data.get(f)) for f in fields).casefold()
            if any(t in hay for t in terms): out.append(item)
        return out

    def _source(self, modulo: str, tipo: str, items: list[dict[str, Any]]) -> AssistiveSource:
        return AssistiveSource(modulo=modulo, tipo=tipo, total=len(items), ids=[str(i.get('id')) for i in items[:5] if i.get('id')])

    def _confianca(self, ctx: dict[str, Any], fontes: list[AssistiveSource]) -> float:
        total = sum(f.total for f in fontes if f.status == 'ok') + (1 if ctx.get('dossie') else 0) + (1 if ctx.get('checklist') else 0)
        return round(min(0.95, 0.2 + total * 0.08), 2) if total else 0.15

    def _org(self, user: dict[str, Any]) -> str:
        return user.get('active_organization_id') or user.get('organization_id') or 'default-org'

    def _dump(self, item: Any) -> dict[str, Any]:
        if hasattr(item, 'model_dump'): return item.model_dump(mode='json')
        if isinstance(item, dict): return item
        return dict(item)

    def _stringify(self, value: Any) -> str:
        if value is None: return ''
        if isinstance(value, list): return ' '.join(self._stringify(v) for v in value)
        if isinstance(value, dict): return ' '.join(self._stringify(v) for v in value.values())
        return str(value)

    def _read_json(self, path: Path) -> list[dict[str, Any]]:
        try: return json.loads(path.read_text(encoding='utf-8'))
        except Exception: return []

    def _write_json(self, path: Path, data: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2, default=str); tmp.write('\n'); tmp_path = Path(tmp.name)
        tmp_path.replace(path)
