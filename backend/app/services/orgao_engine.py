from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.schemas.memory import MemoryCreate
from app.schemas.orgao import (
    OrgaoCreate,
    OrgaoEvent,
    OrgaoEventCreate,
    OrgaoHistoricoResponse,
    OrgaoListResponse,
    OrgaoRecord,
    OrgaoUpdate,
)
from app.services.audit_log import audit_event
from app.services.case_store import JsonCaseStore
from app.services.memory_core_client import MemoryCoreClient
from app.services.orgao_store import HybridOrgaoStore


class LiciOrgaosEngine:
    def __init__(
        self,
        store: HybridOrgaoStore | None = None,
        memory: MemoryCoreClient | None = None,
        case_store: JsonCaseStore | None = None,
    ):
        self.store = store or HybridOrgaoStore()
        self.memory = memory or MemoryCoreClient()
        self.case_store = case_store or JsonCaseStore()

    def info(self) -> dict[str, object]:
        return {
            "nome": "LICI Órgãos Engine",
            "objetivo": "Transformar órgãos compradores em memória estratégica viva para decisão, risco, oportunidade e execução.",
            "endpoints": [
                "GET /orgaos/engine",
                "GET /orgaos",
                "GET /orgaos/{id}",
                "POST /orgaos/registrar",
                "POST /orgaos/{id}/registrar-evento",
                "GET /orgaos/{id}/historico",
            ],
            "persistencia": ["/root/lici-app/orgaos/orgaos.json", "/root/lici-app/orgaos/historico.json"],
            "eventos": [
                "edital publicado",
                "impugnação deferida",
                "impugnação indeferida",
                "recurso acolhido",
                "recurso negado",
                "pagamento atrasado",
                "contrato bem executado",
                "exigência restritiva",
                "concorrência baixa",
                "concorrência alta",
            ],
            "integracoes": ["Memory Core", "Case Engine", "Radar Engine", "Audit Log"],
        }

    def list(self, organization_id: str | None = None) -> OrgaoListResponse:
        orgaos = self.store.list(organization_id=organization_id)
        return OrgaoListResponse(total=len(orgaos), orgaos=orgaos)

    def get(self, orgao_id: str, organization_id: str | None = None) -> OrgaoRecord:
        orgao = self.store.get(orgao_id, organization_id=organization_id)
        if orgao is None:
            if organization_id and self.store.get(orgao_id) is not None:
                audit_event("security", "acesso_negado_cross_org", "erro", {"recurso": "orgao", "orgao_id": orgao_id, "organization_id": organization_id}, orgao_id)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: órgão pertence a outra organização")
            raise HTTPException(status_code=404, detail="órgão não encontrado")
        return orgao

    def registrar(self, payload: OrgaoCreate, organization_id: str | None = None) -> OrgaoRecord:
        if organization_id and not payload.organization_id:
            payload = payload.model_copy(update={"organization_id": organization_id})
        existing = self.store.find_by_nome_cnpj(payload.nome, payload.cnpj)
        if existing and organization_id and (existing.organization_id or "default-org") != organization_id:
            existing = None
        if existing:
            orgao = self._merge(existing, payload)
            action = "atualizacao_orgao"
        else:
            orgao = OrgaoRecord(**payload.model_dump())
            action = "registro_orgao"

        orgao.atualizado_em = self._now()
        orgao = self._recalcular_por_contexto(orgao)
        saved = self.store.upsert(orgao)
        self._registrar_memoria_orgao(saved, action)
        audit_event(
            modulo="orgaos_engine",
            acao=action,
            status="ok",
            detalhes={"nome": saved.nome, "uf": saved.uf, "risco": saved.risco, "score_confiabilidade": saved.score_confiabilidade, "score_oportunidade": saved.score_oportunidade},
            id_relacionado=saved.id,
        )
        return saved

    def atualizar(self, orgao_id: str, payload: OrgaoUpdate, organization_id: str | None = None) -> OrgaoRecord:
        orgao = self.get(orgao_id, organization_id=organization_id)
        data = orgao.model_dump()
        for key, value in payload.model_dump(exclude_unset=True).items():
            if value is not None:
                data[key] = {**data.get(key, {}), **value} if key == 'metadata' else value
        data['atualizado_em'] = self._now()
        updated = self._recalcular_por_contexto(OrgaoRecord(**data))
        saved = self.store.upsert(updated)
        audit_event('orgaos_engine', 'atualizacao_orgao_manual', 'ok', {'nome': saved.nome, 'organization_id': saved.organization_id}, saved.id)
        return saved

    def arquivar(self, orgao_id: str, organization_id: str | None = None) -> OrgaoRecord:
        orgao = self.get(orgao_id, organization_id=organization_id)
        data = orgao.model_dump()
        metadata = dict(data.get('metadata') or {})
        metadata.update({'arquivado': True, 'arquivado_em': self._now()})
        data['metadata'] = metadata
        data['atualizado_em'] = self._now()
        saved = self.store.upsert(OrgaoRecord(**data))
        audit_event('orgaos_engine', 'arquivamento_orgao', 'ok', {'nome': saved.nome}, saved.id)
        return saved

    def registrar_evento(self, orgao_id: str, payload: OrgaoEventCreate, organization_id: str | None = None) -> OrgaoEvent:
        orgao = self.get(orgao_id, organization_id=organization_id)
        if organization_id and not payload.organization_id:
            payload = payload.model_copy(update={"organization_id": organization_id})
        event = OrgaoEvent(orgao_id=orgao_id, **payload.model_dump())
        saved_event = self.store.add_event(event)
        updated = self._aplicar_evento(orgao, saved_event)
        updated.atualizado_em = self._now()
        self.store.upsert(updated)
        self._registrar_memoria_evento(updated, saved_event)
        audit_event(
            modulo="orgaos_engine",
            acao="registro_evento_orgao",
            status="ok",
            detalhes={"orgao": updated.nome, "tipo": saved_event.tipo, "impacto": saved_event.impacto},
            id_relacionado=updated.id,
        )
        return saved_event

    def historico(self, orgao_id: str, organization_id: str | None = None) -> OrgaoHistoricoResponse:
        self.get(orgao_id, organization_id=organization_id)
        eventos = self.store.history(orgao_id)
        return OrgaoHistoricoResponse(orgao_id=orgao_id, total=len(eventos), eventos=eventos)

    def _merge(self, current: OrgaoRecord, payload: OrgaoCreate) -> OrgaoRecord:
        data = current.model_dump()
        incoming = payload.model_dump()
        for key, value in incoming.items():
            if isinstance(value, list):
                data[key] = self._merge_list(data.get(key, []), value)
            elif isinstance(value, dict):
                data[key] = {**data.get(key, {}), **value}
            elif value not in (None, "", "desconhecido"):
                data[key] = value
        return OrgaoRecord(**data)

    def _aplicar_evento(self, orgao: OrgaoRecord, event: OrgaoEvent) -> OrgaoRecord:
        tipo = event.tipo
        if tipo == "impugnação deferida":
            orgao.historico_impugnacoes = self._merge_list(orgao.historico_impugnacoes, [event.descricao])
            orgao.score_oportunidade = min(100, orgao.score_oportunidade + 6)
            orgao.score_confiabilidade = min(100, orgao.score_confiabilidade + 4)
        elif tipo == "impugnação indeferida":
            orgao.historico_impugnacoes = self._merge_list(orgao.historico_impugnacoes, [event.descricao])
            orgao.score_confiabilidade = max(0, orgao.score_confiabilidade - 3)
        elif tipo == "pagamento atrasado":
            orgao.historico_pagamento = self._merge_list(orgao.historico_pagamento, [event.descricao])
            orgao.score_confiabilidade = max(0, orgao.score_confiabilidade - 12)
            orgao.risco = self._worse_risk(orgao.risco, "alto")
        elif tipo == "contrato bem executado":
            orgao.historico_pagamento = self._merge_list(orgao.historico_pagamento, [event.descricao])
            orgao.score_confiabilidade = min(100, orgao.score_confiabilidade + 8)
            orgao.score_oportunidade = min(100, orgao.score_oportunidade + 5)
        elif tipo == "exigência restritiva":
            orgao.exigencias_recorrentes = self._merge_list(orgao.exigencias_recorrentes, [event.descricao])
            orgao.risco = self._worse_risk(orgao.risco, "alto")
        elif tipo == "concorrência baixa":
            orgao.score_oportunidade = min(100, orgao.score_oportunidade + 10)
        elif tipo == "concorrência alta":
            orgao.score_oportunidade = max(0, orgao.score_oportunidade - 8)
        elif tipo == "recurso acolhido":
            orgao.score_confiabilidade = min(100, orgao.score_confiabilidade + 4)
        elif tipo == "recurso negado":
            orgao.score_confiabilidade = max(0, orgao.score_confiabilidade - 2)
        return orgao

    def _recalcular_por_contexto(self, orgao: OrgaoRecord) -> OrgaoRecord:
        casos = [case for case in self.case_store.list(organization_id=orgao.organization_id or "default-org") if case.orgao.strip().lower() == orgao.nome.strip().lower()]
        if casos:
            orgao.metadata = {**orgao.metadata, "casos_relacionados": [case.id for case in casos]}
            orgao.score_oportunidade = min(100, orgao.score_oportunidade + min(15, len(casos) * 3))
        if orgao.risco in {"alto", "crítico"}:
            orgao.score_confiabilidade = max(0, orgao.score_confiabilidade - 5)
        if orgao.exigencias_recorrentes:
            orgao.score_oportunidade = min(100, orgao.score_oportunidade + min(10, len(orgao.exigencias_recorrentes) * 2))
        return orgao

    def _registrar_memoria_orgao(self, orgao: OrgaoRecord, action: str) -> None:
        self.memory.registrar(MemoryCreate(
            tipo="orgao",
            titulo=f"Órgão comprador: {orgao.nome}",
            descricao=f"Órgão {orgao.nome} ({orgao.uf or 'UF não informada'}) registrado no Órgãos Engine.",
            contexto=f"CNPJ: {orgao.cnpj or 'não informado'}; esfera: {orgao.esfera or 'não informada'}; risco: {orgao.risco}.",
            estrategia=orgao.observacoes_estrategicas or "Usar histórico do órgão para calibrar participação, impugnações, recursos, execução e cobrança.",
            aprendizado=orgao.comportamento or "Órgão deve ser acompanhado como ativo estratégico vivo.",
            uso_futuro="Consultar antes de decidir participação, tese de impugnação, estratégia de recurso e risco de execução/pagamento.",
            tags=["orgaos-engine", action, orgao.nome, orgao.uf],
            fonte="orgaos_engine",
            confianca=0.75,
        ))

    def _registrar_memoria_evento(self, orgao: OrgaoRecord, event: OrgaoEvent) -> None:
        self.memory.registrar(MemoryCreate(
            tipo="orgao" if event.tipo not in {"pagamento atrasado", "contrato bem executado"} else "contrato",
            titulo=f"{orgao.nome}: {event.tipo}",
            descricao=event.descricao,
            contexto=f"Órgão: {orgao.nome}; UF: {orgao.uf}; evento: {event.tipo}; caso_id: {event.caso_id or 'não informado'}; radar_id: {event.radar_id or 'não informado'}.",
            estrategia=event.impacto or "Usar evento para ajustar score, risco e estratégia futura contra/para este órgão.",
            aprendizado="Eventos de órgão comprador devem alimentar memória viva, decisão de participação e gestão de risco contratual.",
            uso_futuro="Reutilizar em editais futuros do mesmo órgão e em casos similares.",
            tags=["orgaos-engine", str(event.tipo), orgao.nome, orgao.uf],
            fonte="orgaos_engine",
            confianca=0.8,
        ))

    def _merge_list(self, left: list[str], right: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for item in left + right:
            if not item or item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out

    def _worse_risk(self, current: str, candidate: str) -> str:
        order = {"desconhecido": 0, "baixo": 1, "médio": 2, "alto": 3, "crítico": 4}
        return candidate if order.get(candidate, 0) > order.get(current, 0) else current

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
