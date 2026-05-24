from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.schemas.consultor import (
    ConsultorClienteCreate,
    ConsultorClienteDetalheResponse,
    ConsultorClienteRecord,
    ConsultorClientesResponse,
    ConsultorDemandaCreate,
    ConsultorDemandaRecord,
    ConsultorDemandasResponse,
    ConsultorDemandaStatusUpdate,
)
from app.schemas.memory import MemoryCreate
from app.services.audit_log import audit_event
from app.services.case_store import JsonCaseStore
from app.services.consultor_store import HybridConsultorStore
from app.services.memory_core_client import MemoryCoreClient
from app.services.profile_store import JsonOperationalProfileStore


class LiciConsultorEngine:
    def __init__(
        self,
        store: HybridConsultorStore | None = None,
        case_store: JsonCaseStore | None = None,
        memory: MemoryCoreClient | None = None,
        profile_store: JsonOperationalProfileStore | None = None,
    ):
        self.store = store or HybridConsultorStore()
        self.case_store = case_store or JsonCaseStore()
        self.memory = memory or MemoryCoreClient()
        self.profile_store = profile_store or JsonOperationalProfileStore()

    def info(self) -> dict[str, object]:
        return {
            "nome": "LICI Consultor Engine",
            "objetivo": "Implementar a rota Consultor para gestão de clientes, demandas e atendimento em licitações.",
            "perfil_operacional": "consultor",
            "endpoints": [
                "GET /consultor/engine",
                "GET /consultor/clientes",
                "POST /consultor/clientes",
                "GET /consultor/clientes/{id}",
                "POST /consultor/clientes/{id}/registrar-demanda",
                "GET /consultor/demandas",
                "POST /consultor/demandas/{id}/atualizar-status",
            ],
            "persistencia": [
                "/root/lici-app/consultor/clientes.json",
                "/root/lici-app/consultor/demandas.json",
            ],
            "integracoes": ["Case Engine", "Memory Core", "Audit Log", "Operational Profile Engine"],
            "tipos_demanda": ["edital", "impugnação", "recurso", "habilitação", "proposta", "contrato", "cobrança"],
        }

    def list_clientes(self, organization_id: str | None = None) -> ConsultorClientesResponse:
        clientes = self.store.list_clientes(organization_id=organization_id)
        return ConsultorClientesResponse(total=len(clientes), clientes=clientes)

    def create_cliente(self, payload: ConsultorClienteCreate, organization_id: str | None = None) -> ConsultorClienteRecord:
        if organization_id and not payload.organization_id:
            payload = payload.model_copy(update={"organization_id": organization_id})
        existing = self.store.find_cliente(payload.nome, payload.documento, organization_id=organization_id)
        if existing:
            cliente = self._merge_cliente(existing, payload)
            acao = "atualizacao_cliente"
        else:
            cliente = ConsultorClienteRecord(**payload.model_dump())
            acao = "registro_cliente"
        cliente.atualizado_em = self._now()
        saved = self.store.upsert_cliente(cliente)
        self._registrar_memoria_cliente(saved, acao)
        audit_event(
            modulo="consultor_engine",
            acao=acao,
            status="ok",
            detalhes={"cliente": saved.nome, "segmento": saved.segmento, "status_cliente": saved.status, "score_potencial": saved.score_potencial},
            id_relacionado=saved.id,
        )
        return saved

    def get_cliente(self, cliente_id: str, organization_id: str | None = None) -> ConsultorClienteDetalheResponse:
        cliente = self._get_cliente(cliente_id, organization_id=organization_id)
        demandas = self.store.demandas_cliente(cliente_id, organization_id=organization_id)
        casos = self._casos_relacionados(cliente)
        return ConsultorClienteDetalheResponse(cliente=cliente, demandas=demandas, casos_relacionados=casos)

    def registrar_demanda(self, cliente_id: str, payload: ConsultorDemandaCreate, organization_id: str | None = None) -> ConsultorDemandaRecord:
        cliente = self._get_cliente(cliente_id, organization_id=organization_id)
        if organization_id and not payload.organization_id:
            payload = payload.model_copy(update={"organization_id": organization_id})
        if payload.caso_vivo_id and self.case_store.get(payload.caso_vivo_id, organization_id=organization_id) is None:
            raise HTTPException(status_code=404, detail="caso vivo relacionado não encontrado")
        demanda = ConsultorDemandaRecord(cliente_id=cliente.id, cliente_nome=cliente.nome, **payload.model_dump())
        demanda = self._normalizar_demanda(demanda)
        saved = self.store.upsert_demanda(demanda)
        cliente.atualizado_em = self._now()
        self.store.upsert_cliente(cliente)
        self._registrar_memoria_demanda(cliente, saved, "registro_demanda")
        audit_event(
            modulo="consultor_engine",
            acao="registro_demanda",
            status="ok",
            detalhes={"cliente": cliente.nome, "tipo": saved.tipo, "prazo": saved.prazo, "prioridade": saved.prioridade, "status_demanda": saved.status, "caso_vivo_id": saved.caso_vivo_id},
            id_relacionado=saved.id,
        )
        return saved

    def list_demandas(self, organization_id: str | None = None) -> ConsultorDemandasResponse:
        demandas = self.store.list_demandas(organization_id=organization_id)
        return ConsultorDemandasResponse(total=len(demandas), demandas=demandas)

    def atualizar_status_demanda(self, demanda_id: str, payload: ConsultorDemandaStatusUpdate, organization_id: str | None = None) -> ConsultorDemandaRecord:
        demanda = self.store.get_demanda(demanda_id, organization_id=organization_id)
        if demanda is None:
            if organization_id and self.store.get_demanda(demanda_id) is not None:
                audit_event("security", "acesso_negado_cross_org", "erro", {"recurso": "demanda", "demanda_id": demanda_id, "organization_id": organization_id}, demanda_id)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: demanda pertence a outra organização")
            raise HTTPException(status_code=404, detail="demanda não encontrada")
        demanda.status = payload.status
        demanda.atualizado_em = self._now()
        if payload.observacao:
            demanda.metadata = {**demanda.metadata, "ultima_observacao": payload.observacao}
        demanda = self._normalizar_demanda(demanda)
        saved = self.store.upsert_demanda(demanda)
        cliente = self.store.get_cliente(saved.cliente_id)
        if cliente:
            cliente.atualizado_em = self._now()
            self.store.upsert_cliente(cliente)
            self._registrar_memoria_demanda(cliente, saved, "atualizacao_status_demanda", payload.observacao)
        audit_event(
            modulo="consultor_engine",
            acao="atualizacao_status_demanda",
            status="ok",
            detalhes={"demanda": saved.id, "cliente": saved.cliente_nome, "novo_status": saved.status, "observacao": payload.observacao},
            id_relacionado=saved.id,
        )
        return saved

    def _get_cliente(self, cliente_id: str, organization_id: str | None = None) -> ConsultorClienteRecord:
        cliente = self.store.get_cliente(cliente_id, organization_id=organization_id)
        if cliente is None:
            if organization_id and self.store.get_cliente(cliente_id) is not None:
                audit_event("security", "acesso_negado_cross_org", "erro", {"recurso": "cliente", "cliente_id": cliente_id, "organization_id": organization_id}, cliente_id)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: cliente pertence a outra organização")
            raise HTTPException(status_code=404, detail="cliente não encontrado")
        return cliente

    def _merge_cliente(self, current: ConsultorClienteRecord, payload: ConsultorClienteCreate) -> ConsultorClienteRecord:
        data = current.model_dump()
        incoming = payload.model_dump()
        for key, value in incoming.items():
            if isinstance(value, list):
                data[key] = self._merge_list(data.get(key, []), value)
            elif isinstance(value, dict):
                data[key] = {**data.get(key, {}), **value}
            elif value not in (None, ""):
                data[key] = value
        return ConsultorClienteRecord(**data)

    def _normalizar_demanda(self, demanda: ConsultorDemandaRecord) -> ConsultorDemandaRecord:
        if demanda.prioridade == "crítica" and demanda.status == "aberta":
            demanda.metadata = {**demanda.metadata, "acao_recomendada": "Tratar imediatamente e controlar prazo de entrega ao cliente."}
        if demanda.tipo == "cobrança" and demanda.status == "aberta":
            demanda.metadata = {**demanda.metadata, "acao_recomendada": "Validar contrato, valores e enviar cobrança ao cliente."}
        return demanda

    def _casos_relacionados(self, cliente: ConsultorClienteRecord) -> list[dict]:
        related = []
        for case in self.case_store.list():
            if case.cliente.strip().lower() == cliente.nome.strip().lower() or case.cliente.strip().lower() == cliente.documento.strip().lower():
                related.append({
                    "id": case.id,
                    "orgao": case.orgao,
                    "objeto": case.objeto,
                    "fase_atual": case.fase_atual,
                    "status": case.status,
                    "score_estrategico": case.score_estrategico,
                })
        return related

    def _registrar_memoria_cliente(self, cliente: ConsultorClienteRecord, acao: str) -> None:
        self.memory.registrar(MemoryCreate(
            tipo="padrao",
            titulo=f"Cliente consultoria: {cliente.nome}",
            descricao=f"Cliente {cliente.nome} registrado/atualizado no Consultor Engine.",
            contexto=f"Documento: {cliente.documento or 'não informado'}; segmento: {cliente.segmento or 'não informado'}; UF: {cliente.uf or 'não informada'}; status: {cliente.status}.",
            estrategia=cliente.observacoes or "Gerenciar cliente por demandas, prazos, peças, relatórios e recorrência.",
            aprendizado="Clientes de consultoria precisam de histórico operacional, potencial, demandas e atendimento rastreável.",
            uso_futuro="Usar no dashboard consultor, carteira, relatórios para cliente e priorização de atendimento.",
            tags=["consultor-engine", acao, cliente.nome, cliente.uf, cliente.segmento],
            fonte="consultor_engine",
            confianca=0.75,
        ))

    def _registrar_memoria_demanda(self, cliente: ConsultorClienteRecord, demanda: ConsultorDemandaRecord, acao: str, observacao: str = "") -> None:
        self.memory.registrar(MemoryCreate(
            tipo="padrao",
            titulo=f"Demanda {demanda.tipo}: {cliente.nome}",
            descricao=demanda.descricao,
            contexto=f"Cliente: {cliente.nome}; prazo: {demanda.prazo or 'não informado'}; prioridade: {demanda.prioridade}; status: {demanda.status}; caso_vivo_id: {demanda.caso_vivo_id or 'não informado'}. {observacao}",
            estrategia="Controlar prazo, entrega e comunicação com o cliente; transformar demanda em caso vivo quando houver licitação relevante.",
            aprendizado="Demandas de consultoria devem alimentar histórico de atendimento, produtividade, recorrência e relatórios ao cliente.",
            uso_futuro="Reutilizar em relatórios do cliente, dashboard consultor e avaliação de produtividade/cobrança.",
            tags=["consultor-engine", acao, str(demanda.tipo), str(demanda.status), cliente.nome],
            fonte="consultor_engine",
            confianca=0.8,
        ))

    def _merge_list(self, left: list[str], right: list[str]) -> list[str]:
        out = []
        seen = set()
        for item in left + right:
            if not item or item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
