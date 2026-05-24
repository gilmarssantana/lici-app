from __future__ import annotations

import json
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.chat import ChatFonte, ChatMessageRequest, ChatMessageResponse
from app.schemas.decision import DecisionRequest
from app.services.audit_log import audit_event
from app.services.case_store import HybridCaseStore
from app.services.chat_telemetry import LiciChatTelemetry
from app.services.consultor_store import HybridConsultorStore
from app.services.concorrente_store import HybridConcorrenteStore
from app.services.decision_engine import LiciDecisionEngine
from app.services.document_generator import LiciDocumentGenerator
from app.services.global_search import LiciGlobalSearchService
from app.services.memory_store import HybridMemoryStore
from app.services.orgao_store import HybridOrgaoStore
from app.services.radar_store import HybridRadarStore

CHAT_ROOT = Path("/root/lici-app/chat")
CONVERSAS_PATH = CHAT_ROOT / "conversas.json"


class LiciChatEngine:
    """LICI Chat operacional: determinístico, auditável e sem chamada a IA externa."""

    def __init__(self):
        CHAT_ROOT.mkdir(parents=True, exist_ok=True)
        if not CONVERSAS_PATH.exists():
            self._write_json({"conversas": []})
        self.global_search = LiciGlobalSearchService()
        self.memory_store = HybridMemoryStore(settings.memory_root)
        self.case_store = HybridCaseStore()
        self.radar_store = HybridRadarStore()
        self.orgao_store = HybridOrgaoStore()
        self.consultor_store = HybridConsultorStore()
        self.concorrente_store = HybridConcorrenteStore()
        self.decision_engine = LiciDecisionEngine()
        self.document_generator = LiciDocumentGenerator()
        self.telemetry = LiciChatTelemetry()

    def engine_info(self) -> dict[str, Any]:
        return {
            "nome": "LICI Chat Operacional",
            "status": "ativo",
            "modo": "deterministico_sem_ia_externa",
            "endpoints": ["GET /chat/engine", "POST /chat/mensagem", "GET /chat/historico", "GET /chat/conversas", "GET /chat/metricas"],
            "intencoes": ["caso", "edital", "memoria", "oportunidade", "orgao", "concorrente", "cliente_consultor", "peca", "decisao", "busca_geral"],
            "ferramentas": ["Busca Global", "Memory Core", "Case Engine", "Radar", "Órgãos", "Concorrentes", "Consultor", "Decision Engine", "Document Generator"],
            "persistencia": {"conversas": str(CONVERSAS_PATH), "metricas": "/root/lici-app/chat/metricas.json", "postgresql": ["chat_sessions", "chat_messages", "chat_metrics"]},
            "regras": ["não chama IA externa", "não inventa resposta", "responde apenas com dados internos", "registra Audit Log", "protegido por JWT/permissões"],
        }

    def conversar(self, payload: ChatMessageRequest, user: dict[str, Any]) -> ChatMessageResponse:
        started = time.perf_counter()
        pergunta = payload.pergunta.strip()
        intencao = self.identificar_intencao(pergunta)
        fontes: list[ChatFonte] = []
        errors: list[str] = []
        try:
            organization_id = user.get("active_organization_id") or user.get("organization_id") or "default-org"
            dados = self._consultar_ferramentas(pergunta, intencao, fontes, organization_id=organization_id)
            resposta, encontrou = self._montar_resposta(pergunta, intencao, dados, fontes)
            errors = [f"{f.modulo}: {f.detalhe}" for f in fontes if f.status == "erro"]

            now = datetime.now(timezone.utc)
            conversa_id = payload.conversa_id or self._new_id("chat")
            mensagem_id = self._new_id("msg")
            response = ChatMessageResponse(
                conversa_id=conversa_id,
                mensagem_id=mensagem_id,
                intencao=intencao,
                pergunta=pergunta,
                resposta=resposta,
                fontes=fontes,
                dados=dados,
                encontrou_dados=encontrou,
                criado_em=now,
            )
            response_time_ms = round((time.perf_counter() - started) * 1000, 2)
            session_record = self._append_message(conversa_id, response, user, payload.contexto, response_time_ms=response_time_ms)
            tools_used = [f.modulo for f in fontes]
            metric = {
                "session_id": conversa_id,
                "message_id": mensagem_id,
                "intent": intencao,
                "tools_used": tools_used,
                "success": not errors,
                "found_data": encontrou,
                "response_time_ms": response_time_ms,
                "conversation_size": session_record.get("message_count", 1),
                "user_id": user.get("id"),
                "username": user.get("usuario"),
                "profile": user.get("perfil"),
                "operational_profile": user.get("perfil_operacional") or user.get("perfil"),
                "organization_id": organization_id,
                "endpoint": "POST /chat/mensagem",
                "errors": errors,
                "question": pergunta,
            }
            message_record = {
                "id": mensagem_id,
                "session_id": conversa_id,
                "intent": intencao,
                "question": pergunta,
                "answer": resposta,
                "found_data": encontrou,
                "tools_used": tools_used,
                "sources": [f.model_dump() for f in fontes],
                "user_id": user.get("id"),
                "username": user.get("usuario"),
                "profile": user.get("perfil"),
                "organization_id": organization_id,
                "endpoint": "POST /chat/mensagem",
                "response_time_ms": response_time_ms,
                "created_at": now.isoformat(),
            }
            self.telemetry.record_message(session=session_record, message=message_record, metric=metric)
            audit_event(
                "chat_engine",
                "mensagem_processada",
                "ok" if not errors else "alerta",
                {"conversa_id": conversa_id, "mensagem_id": mensagem_id, "intencao": intencao, "fontes": tools_used, "encontrou_dados": encontrou, "tempo_ms": response_time_ms, "erros": errors},
                conversa_id,
            )
            return response
        except Exception as exc:
            self.telemetry.record_endpoint_error("POST /chat/mensagem", user, exc)
            raise

    def historico(self, conversa_id: str | None = None, limite: int = 100, organization_id: str | None = None) -> dict[str, Any]:
        data = self._read_json()
        mensagens: list[dict[str, Any]] = []
        for conversa in data.get("conversas", []):
            if conversa_id and conversa.get("id") != conversa_id:
                continue
            if organization_id and (conversa.get("organization_id") or "default-org") != organization_id:
                if conversa_id:
                    audit_event("security", "acesso_negado_cross_org", "erro", {"recurso": "chat_session", "conversa_id": conversa_id, "organization_id": organization_id, "record_organization_id": conversa.get("organization_id") or "default-org"}, conversa_id)
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: conversa pertence a outra organização")
                continue
            for msg in conversa.get("mensagens", []):
                mensagens.append({"conversa_id": conversa.get("id"), **msg})
        mensagens = sorted(mensagens, key=lambda item: item.get("criado_em", ""), reverse=True)[: max(1, min(limite, 500))]
        return {"conversa_id": conversa_id, "total": len(mensagens), "mensagens": mensagens}

    def conversas(self, organization_id: str | None = None) -> dict[str, Any]:
        data = self._read_json()
        conversas = []
        for conversa in data.get("conversas", []):
            if organization_id and (conversa.get("organization_id") or "default-org") != organization_id:
                continue
            conversas.append({
                "id": conversa.get("id"),
                "titulo": conversa.get("titulo") or "Conversa LICI",
                "intencao_principal": conversa.get("intencao_principal"),
                "total_mensagens": len(conversa.get("mensagens", [])),
                "criado_em": conversa.get("criado_em"),
                "atualizado_em": conversa.get("atualizado_em"),
            })
        conversas.sort(key=lambda item: item.get("atualizado_em") or "", reverse=True)
        return {"total": len(conversas), "conversas": conversas}

    def metricas(self) -> dict[str, Any]:
        return self.telemetry.metrics_summary()

    def identificar_intencao(self, pergunta: str) -> str:
        texto = pergunta.casefold()
        checks = [
            ("concorrente", ["concorrente", "concorrentes", "competidor", "competidores", "inabilitado", "preço muito baixo", "comportamento agressivo"]),
            ("cliente_consultor", ["cliente", "consultor", "demanda", "carteira"]),
            ("oportunidade", ["oportunidade", "radar", "pncp", "triagem"]),
            ("memoria", ["memória", "memoria", "aprendizado", "tese", "padrão", "padrao", "histórico"]),
            ("orgao", ["órgão", "orgao", "prefeitura", "secretaria", "autarquia", "cnpj"]),
            ("peca", ["peça", "peca", "impugnação", "impugnacao", "recurso", "contrarrazões", "contrarrazoes", "documento gerado"]),
            ("decisao", ["decisão", "decisao", "vale a pena", "participar", "impugnar", "desistir", "estratégia híbrida", "go no go", "go/no-go"]),
            ("edital", ["edital", "termo de referência", "tr", "habilitação", "habilitacao", "proposta", "julgamento", "lei 14.133", "lei 13303"]),
            ("caso", ["caso", "timeline", "fase", "homologação", "contrato", "execução", "pagamento"]),
        ]
        for intent, terms in checks:
            if any(term in texto for term in terms):
                return intent
        return "busca_geral"

    def _consultar_ferramentas(self, pergunta: str, intencao: str, fontes: list[ChatFonte], organization_id: str | None = None) -> dict[str, Any]:
        dados: dict[str, Any] = {}
        global_result = self._safe("Busca Global", lambda: self.global_search.search(pergunta, limit=5), fontes)
        if global_result is not None:
            dados["busca_global"] = global_result
            fontes.append(ChatFonte(modulo="Busca Global", tipo="busca", total=global_result.get("total", 0), ids=[str(i.get("id")) for i in global_result.get("flat", [])[:5] if i.get("id")]))

        if intencao in {"memoria", "edital", "decisao", "busca_geral"}:
            items = self._safe("Memory Core", lambda: self.memory_store.search(pergunta, organization_id=organization_id)[:5], fontes)
            if items is not None:
                dados["memorias"] = [self._dump(item) for item in items]
                fontes.append(ChatFonte(modulo="Memory Core", tipo="memoria", total=len(items), ids=[str(getattr(i, "id", "")) for i in items if getattr(i, "id", None)]))

        if intencao in {"caso", "edital", "decisao", "busca_geral"}:
            casos = self._match_list(self.case_store.list(organization_id=organization_id), pergunta, ["id", "cliente", "orgao", "objeto", "modalidade", "fase_atual", "status", "riscos", "oportunidades"])
            dados["casos"] = [self._dump(item) for item in casos[:5]]
            fontes.append(ChatFonte(modulo="Case Engine", tipo="caso", total=len(casos[:5]), ids=[str(getattr(i, "id", "")) for i in casos[:5] if getattr(i, "id", None)]))

        if intencao in {"oportunidade", "edital", "decisao", "busca_geral"}:
            oportunidades = self._match_list(self.radar_store.list(), pergunta, ["id", "pncp_id", "orgao", "uf", "objeto", "modalidade", "status", "classificacao_triagem"])
            dados["oportunidades"] = [self._dump(item) for item in oportunidades[:5]]
            fontes.append(ChatFonte(modulo="Radar", tipo="oportunidade", total=len(oportunidades[:5]), ids=[str(getattr(i, "id", "")) for i in oportunidades[:5] if getattr(i, "id", None)]))

        if intencao in {"orgao", "edital", "decisao", "busca_geral"}:
            orgaos = self._match_list(self.orgao_store.list(), pergunta, ["id", "nome", "cnpj", "uf", "esfera", "poder", "perfil", "observacoes"])
            dados["orgaos"] = [self._dump(item) for item in orgaos[:5]]
            fontes.append(ChatFonte(modulo="Órgãos", tipo="orgao", total=len(orgaos[:5]), ids=[str(getattr(i, "id", "")) for i in orgaos[:5] if getattr(i, "id", None)]))

        if intencao in {"concorrente", "edital", "decisao", "busca_geral"}:
            concorrentes = self._match_list(self.concorrente_store.list(), pergunta, ["id", "nome", "cnpj", "segmento", "uf", "observacoes_estrategicas", "risco_operacional", "padroes_documentais", "padroes_preco", "orgaos_relacionados", "casos_relacionados"])
            dados["concorrentes"] = [self._dump(item) for item in concorrentes[:5]]
            fontes.append(ChatFonte(modulo="Concorrentes", tipo="concorrente", total=len(concorrentes[:5]), ids=[str(getattr(i, "id", "")) for i in concorrentes[:5] if getattr(i, "id", None)]))

        if intencao in {"cliente_consultor", "decisao", "busca_geral"}:
            clientes = self._match_list(self.consultor_store.list_clientes(), pergunta, ["id", "nome", "documento", "segmento", "uf", "status", "observacoes", "contatos"])
            demandas = self._match_list(self.consultor_store.list_demandas(), pergunta, ["id", "cliente_id", "titulo", "descricao", "status", "prioridade", "prazo"])
            dados["clientes_consultor"] = [self._dump(item) for item in clientes[:5]]
            dados["demandas_consultor"] = [self._dump(item) for item in demandas[:5]]
            fontes.append(ChatFonte(modulo="Consultor", tipo="cliente_demanda", total=len(clientes[:5]) + len(demandas[:5]), ids=[str(getattr(i, "id", "")) for i in (clientes[:5] + demandas[:5]) if getattr(i, "id", None)]))

        if intencao in {"peca", "edital", "decisao", "busca_geral"}:
            docs = self._match_list(self.document_generator.list_generated().documentos, pergunta, ["id", "tipo", "titulo", "cliente", "orgao", "processo", "modalidade", "objeto", "decisao_base"])
            dados["documentos_gerados"] = [self._dump(item) for item in docs[:5]]
            fontes.append(ChatFonte(modulo="Document Generator", tipo="peca", total=len(docs[:5]), ids=[str(getattr(i, "id", "")) for i in docs[:5] if getattr(i, "id", None)]))

        if intencao == "decisao":
            decisao = self._safe("Decision Engine", lambda: self.decision_engine.decidir(DecisionRequest(pergunta=pergunta, consultar_rag=False)).model_dump(mode="json"), fontes)
            if decisao is not None:
                dados["decisao"] = decisao
                fontes.append(ChatFonte(modulo="Decision Engine", tipo="decisao", total=1, ids=[]))
        return dados

    def _montar_resposta(self, pergunta: str, intencao: str, dados: dict[str, Any], fontes: list[ChatFonte]) -> tuple[str, bool]:
        encontrados = self._total_encontrado(dados)
        if encontrados == 0 and "decisao" not in dados:
            return (
                f"Não encontrei dados internos suficientes para responder com segurança sobre: “{pergunta}”. "
                "Consultei as ferramentas disponíveis e não vou inventar uma resposta. Próximo passo: envie órgão, objeto, número do edital/caso, cliente ou palavra-chave mais específica.",
                False,
            )

        partes = [f"Intenção identificada: {self._label(intencao)}."]
        if intencao == "decisao" and dados.get("decisao"):
            d = dados["decisao"]
            partes.append(f"Decision Engine: {d.get('decisao')} com score {d.get('score')}/100.")
            partes.append(d.get("justificativa_objetiva", ""))
            riscos = d.get("riscos_criticos") or []
            if riscos:
                partes.append("Riscos críticos: " + "; ".join(riscos[:4]))
            partes.append("Ação imediata: " + (d.get("acao_imediata") or "validar dados do edital/caso antes de agir."))

        for key, label in [
            ("casos", "Casos encontrados"),
            ("memorias", "Memórias relevantes"),
            ("oportunidades", "Oportunidades do Radar"),
            ("orgaos", "Órgãos encontrados"),
            ("concorrentes", "Concorrentes encontrados"),
            ("clientes_consultor", "Clientes consultor"),
            ("demandas_consultor", "Demandas consultor"),
            ("documentos_gerados", "Peças/documentos gerados"),
        ]:
            items = dados.get(key) or []
            if items:
                partes.append(self._summarize_items(label, items))

        if dados.get("busca_global", {}).get("total", 0):
            partes.append(f"Busca Global localizou {dados['busca_global']['total']} resultado(s) relacionados.")

        partes.append("Fonte da resposta: somente módulos internos da LICI; nenhuma IA externa foi chamada.")
        return "\n\n".join(p for p in partes if p), True

    def _summarize_items(self, label: str, items: list[dict[str, Any]]) -> str:
        lines = [f"{label}:"]
        for item in items[:3]:
            title = item.get("titulo") or item.get("nome") or item.get("orgao") or item.get("cliente") or item.get("objeto") or item.get("id")
            detail = item.get("objeto") or item.get("descricao") or item.get("status") or item.get("fase_atual") or item.get("tipo") or ""
            score = item.get("score_estrategico") or item.get("score_preliminar") or item.get("score_base")
            suffix = f" | score {score}" if score is not None else ""
            lines.append(f"- {title}: {detail}{suffix}")
        if len(items) > 3:
            lines.append(f"- +{len(items) - 3} registro(s) adicional(is).")
        return "\n".join(lines)

    def _append_message(self, conversa_id: str, response: ChatMessageResponse, user: dict[str, Any], contexto: dict[str, Any] | None, response_time_ms: float = 0) -> dict[str, Any]:
        data = self._read_json()
        now = response.criado_em.isoformat()
        conversa = next((c for c in data.get("conversas", []) if c.get("id") == conversa_id), None)
        if conversa is None:
            conversa = {
                "id": conversa_id,
                "titulo": self._title(response.pergunta),
                "intencao_principal": response.intencao,
                "criado_em": now,
                "atualizado_em": now,
                "organization_id": user.get("active_organization_id") or user.get("organization_id") or "default-org",
                "mensagens": [],
            }
            data.setdefault("conversas", []).append(conversa)
        conversa["atualizado_em"] = now
        conversa.setdefault("mensagens", []).append({
            "id": response.mensagem_id,
            "pergunta": response.pergunta,
            "resposta": response.resposta,
            "intencao": response.intencao,
            "fontes": [f.model_dump() for f in response.fontes],
            "dados_resumo": {k: len(v) if isinstance(v, list) else (v.get("total") if isinstance(v, dict) else 1) for k, v in response.dados.items()},
            "encontrou_dados": response.encontrou_dados,
            "usuario": {"id": user.get("id"), "usuario": user.get("usuario"), "perfil": user.get("perfil"), "perfil_operacional": user.get("perfil_operacional")},
            "organization_id": user.get("active_organization_id") or user.get("organization_id") or "default-org",
            "contexto": contexto or {},
            "tempo_resposta_ms": response_time_ms,
            "criado_em": now,
        })
        message_count = len(conversa.get("mensagens", []))
        session_record = {
            "id": conversa_id,
            "title": conversa.get("titulo"),
            "intent_primary": conversa.get("intencao_principal"),
            "user_id": user.get("id"),
            "username": user.get("usuario"),
            "profile": user.get("perfil"),
            "operational_profile": user.get("perfil_operacional") or user.get("perfil"),
            "organization_id": user.get("active_organization_id") or user.get("organization_id") or "default-org",
            "status": "ativa",
            "message_count": message_count,
            "created_at": conversa.get("criado_em"),
            "updated_at": conversa.get("atualizado_em"),
        }
        self._write_json(data)
        return session_record

    def _read_json(self) -> dict[str, Any]:
        try:
            return json.loads(CONVERSAS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"conversas": []}

    def _write_json(self, data: dict[str, Any]) -> None:
        CHAT_ROOT.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=CHAT_ROOT, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        tmp_path.replace(CONVERSAS_PATH)

    def _safe(self, modulo: str, fn, fontes: list[ChatFonte]) -> Any:
        try:
            return fn()
        except Exception as exc:
            fontes.append(ChatFonte(modulo=modulo, tipo="erro", total=0, status="erro", detalhe=str(exc)))
            return None

    def _match_list(self, items: list[Any], pergunta: str, fields: list[str]) -> list[Any]:
        terms = self._terms(pergunta)
        if not terms:
            return items[:5]
        matched = []
        for item in items:
            data = self._dump(item)
            hay = " ".join(self._stringify(data.get(field)) for field in fields).casefold()
            if any(term in hay for term in terms):
                matched.append(item)
        return matched

    def _terms(self, pergunta: str) -> list[str]:
        stop = {"qual", "quais", "sobre", "para", "com", "uma", "um", "dos", "das", "que", "tem", "esse", "essa", "listar", "mostre", "fale", "me"}
        return [t.casefold() for t in re.findall(r"[\wÀ-ÿ]{3,}", pergunta) if t.casefold() not in stop]

    def _dump(self, item: Any) -> dict[str, Any]:
        if hasattr(item, "model_dump"):
            return item.model_dump(mode="json")
        if isinstance(item, dict):
            return item
        return dict(item)

    def _stringify(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return " ".join(self._stringify(v) for v in value)
        if isinstance(value, dict):
            return " ".join(self._stringify(v) for v in value.values())
        return str(value)

    def _total_encontrado(self, dados: dict[str, Any]) -> int:
        total = 0
        for key, value in dados.items():
            if key == "busca_global" and isinstance(value, dict):
                total += int(value.get("total") or 0)
            elif key == "decisao":
                total += 1
            elif isinstance(value, list):
                total += len(value)
        return total

    def _label(self, intencao: str) -> str:
        return {
            "caso": "caso",
            "edital": "edital/habilitação",
            "memoria": "memória viva",
            "oportunidade": "oportunidade/radar",
            "orgao": "órgão",
            "cliente_consultor": "cliente consultor",
            "peca": "peça/documento",
            "decisao": "decisão operacional",
            "busca_geral": "busca geral",
        }.get(intencao, intencao)

    def _title(self, pergunta: str) -> str:
        compact = " ".join(pergunta.split())
        return compact[:80] or "Conversa LICI"

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"
