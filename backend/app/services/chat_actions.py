from __future__ import annotations

import json
import os
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException, status

from app.api.security import has_permission
from app.core.config import settings
from app.schemas.case import CaseCreate
from app.schemas.chat_action import ChatActionRequest, ChatActionResponse
from app.schemas.consultor import ConsultorDemandaCreate
from app.schemas.document_generator import DocumentGenerateRequest
from app.schemas.edital import EditalAnalyzeTextRequest, EditalChecklistRequest
from app.schemas.memory import MemoryCreate
from app.services.audit_log import audit_event
from app.services.case_engine import LiciCaseEngine
from app.services.chat_telemetry import LiciChatTelemetry
from app.services.consultor_engine import LiciConsultorEngine
from app.services.document_generator import LiciDocumentGenerator
from app.services.edital_analyzer import LiciEditalAnalyzer
from app.services.memory_store import HybridMemoryStore
from app.services.observability import structured_log
from app.services.orgao_store import HybridOrgaoStore

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

CHAT_ROOT = Path("/root/lici-app/chat")
ACTIONS_PATH = CHAT_ROOT / "acoes.json"
POSTGRES_ENV_FILE = Path("/root/lici-app/secrets/postgres.env")


class LiciChatActions:
    def __init__(self):
        CHAT_ROOT.mkdir(parents=True, exist_ok=True)
        if not ACTIONS_PATH.exists():
            self._write_json({"solicitacoes": [], "execucoes": []})
        self.case_engine = LiciCaseEngine()
        self.document_generator = LiciDocumentGenerator()
        self.memory_store = HybridMemoryStore(settings.memory_root)
        self.edital_analyzer = LiciEditalAnalyzer()
        self.orgao_store = HybridOrgaoStore()
        self.consultor_engine = LiciConsultorEngine()
        self.telemetry = LiciChatTelemetry()
        self.dsn = os.getenv("LICI_DATABASE_URL") or self._dsn_from_env_file()
        self._ensure_pg()

    def handle(self, payload: ChatActionRequest, user: dict[str, Any]) -> ChatActionResponse:
        started = time.perf_counter()
        if payload.cancelar:
            response = self._cancel(payload.acao_id, user)
            self._record_action_metric(response, user, round((time.perf_counter() - started) * 1000, 2), cancelled=True)
            return response
        if payload.confirmar:
            response = self._execute(payload.acao_id, user)
            self._record_action_metric(response, user, round((time.perf_counter() - started) * 1000, 2))
            return response
        response = self._preview(payload, user)
        self._record_action_metric(response, user, round((time.perf_counter() - started) * 1000, 2))
        return response

    def metricas_acoes(self) -> dict[str, Any]:
        data = self._read_json()
        execs = data.get("execucoes", [])
        reqs = data.get("solicitacoes", [])
        total_exec = len(execs)
        ok = [e for e in execs if e.get("status") == "executada"]
        cancelled = [r for r in reqs if r.get("status") == "cancelada"]
        errors = [e for e in execs if e.get("status") == "erro"]
        return {
            "solicitacoes_total": len(reqs),
            "execucoes_total": total_exec,
            "taxa_sucesso_acoes": round((len(ok) / total_exec) * 100, 2) if total_exec else 0,
            "acoes_canceladas": len(cancelled),
            "erros_acoes": len(errors),
            "top_acoes": [{"valor": k, "total": v} for k, v in Counter([r.get("acao") for r in reqs]).most_common(10)],
            "erros_recentes": errors[-10:],
            "persistencia": {"json": str(ACTIONS_PATH), "postgresql": self._pg_available()},
        }

    def _preview(self, payload: ChatActionRequest, user: dict[str, Any]) -> ChatActionResponse:
        action = payload.acao or self._detect_action(payload.pergunta)
        params = self._normalize_params(action, payload.parametros, payload.pergunta)
        missing = self._missing(action, params)
        action_id = f"act_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        response = ChatActionResponse(
            acao_id=action_id,
            acao=action,
            status="pendente",
            intencao="acao_operacional",
            parametros=params,
            parametros_faltantes=missing,
            previa=self._preview_text(action, params, missing),
            requer_confirmacao=True,
            fontes=["Chat Actions", self._target_module(action)],
            criado_em=now,
            atualizado_em=now,
        )
        self._save_request(response, user, payload.conversa_id)
        audit_event("chat_actions", "previa_acao", "ok", {"acao": action, "faltantes": missing}, action_id)
        return response

    def _cancel(self, action_id: str | None, user: dict[str, Any]) -> ChatActionResponse:
        record = self._get_request(action_id)
        if not self._can_cancel(record, user):
            owner = (record.get("usuario") or {})
            details = {
                "acao_id": record.get("acao_id"),
                "acao": record.get("acao"),
                "usuario_tentativa": user.get("usuario"),
                "usuario_tentativa_id": user.get("id"),
                "criador": owner.get("usuario"),
                "criador_id": owner.get("id"),
                "motivo": "cancelamento_cross_user_negado",
            }
            audit_event("chat_actions", "tentativa_cancelamento_negada", "erro", details, record.get("acao_id"))
            structured_log("api", "chat_action_cancel_forbidden", "erro", details)
            self._record_security_metric(record, user, "cancelamento_cross_user_negado")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Somente o criador da ação ou admin pode cancelar esta ação")
        record["status"] = "cancelada"
        record["atualizado_em"] = datetime.now(timezone.utc).isoformat()
        self._update_request(record)
        response = self._response_from_record(record, resultado={"cancelado_por": user.get("usuario")})
        audit_event("chat_actions", "acao_cancelada", "ok", {"acao": response.acao, "usuario": user.get("usuario")}, response.acao_id)
        return response

    def _execute(self, action_id: str | None, user: dict[str, Any]) -> ChatActionResponse:
        record = self._get_request(action_id)
        if record.get("status") == "cancelada":
            raise HTTPException(status_code=400, detail="ação já cancelada")
        action = record["acao"]
        params = record.get("parametros") or {}
        missing = self._missing(action, params)
        if missing:
            raise HTTPException(status_code=400, detail={"erro": "parâmetros obrigatórios ausentes", "faltantes": missing})
        self._require_action_permission(action, user)
        if not self._same_org(record, user):
            details = {"acao_id": record.get("acao_id"), "acao": action, "organization_id": self._org_id(user), "record_organization_id": record.get("organization_id"), "motivo": "execucao_cross_org_negada"}
            audit_event("chat_actions", "tentativa_execucao_cross_org_negada", "erro", details, action_id)
            structured_log("api", "chat_action_execute_cross_org_forbidden", "erro", details)
            self._record_security_metric(record, user, "execucao_cross_org_negada")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ação pertence a outra organização")
        try:
            result = self._execute_action(action, params, user=user)
            status_value = "executada"
            error = ""
        except Exception as exc:
            result = None
            status_value = "erro"
            error = str(exc)
            structured_log("api", "chat_action_execution_failed", "erro", {"acao": action, "acao_id": action_id, "erro": error})
            audit_event("chat_actions", "erro_execucao_acao", "erro", {"acao": action, "erro": error}, action_id)
        record.update({"status": status_value, "resultado": result, "erro": error, "atualizado_em": datetime.now(timezone.utc).isoformat()})
        self._update_request(record)
        self._save_execution(record, user)
        response = self._response_from_record(record, resultado=result)
        audit_event("chat_actions", "acao_executada" if status_value == "executada" else "acao_erro", "ok" if status_value == "executada" else "erro", {"acao": action, "erro": error}, action_id)
        return response

    def _execute_action(self, action: str, params: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
        organization_id = self._org_id(user)
        params = dict(params or {})
        params.setdefault("organization_id", organization_id)
        if action == "criar_caso":
            obj = self.case_engine.create_case(CaseCreate(**params), organization_id=organization_id)
            return {"tipo": "caso", "id": obj.id, "orgao": obj.orgao, "objeto": obj.objeto, "score": obj.score_estrategico}
        if action == "gerar_peca":
            tipo = params.pop("tipo_peca", "impugnacao")
            req = DocumentGenerateRequest(**params)
            if tipo == "recurso":
                doc = self.document_generator.gerar_recurso(req)
            elif tipo == "contrarrazoes":
                doc = self.document_generator.gerar_contrarrazoes(req)
            else:
                doc = self.document_generator.gerar_impugnacao(req)
            return {"tipo": "documento", "id": doc.documento.id, "arquivo": doc.documento.arquivo, "titulo": doc.documento.titulo}
        if action == "registrar_memoria":
            mem = self.memory_store.create(MemoryCreate(**params), organization_id=organization_id)
            return {"tipo": "memoria", "id": mem.id, "titulo": mem.titulo}
        if action == "analisar_edital":
            analysis = self.edital_analyzer.analisar_texto(EditalAnalyzeTextRequest(**params))
            return analysis.model_dump(mode="json")
        if action == "consultar_orgao":
            termo = (params.get("orgao_id") or params.get("nome") or "").casefold()
            items = [o for o in self.orgao_store.list() if ((getattr(o, "organization_id", None) or "default-org") == organization_id) and (termo in o.id.casefold() or termo in o.nome.casefold())]
            return {"total": len(items), "orgaos": [i.model_dump(mode="json") for i in items[:5]]}
        if action == "criar_demanda_consultor":
            cliente_id = params.pop("cliente_id")
            demanda = self.consultor_engine.registrar_demanda(cliente_id, ConsultorDemandaCreate(**params), organization_id=organization_id)
            return {"tipo": "demanda", "id": demanda.id, "cliente_id": demanda.cliente_id, "status": demanda.status}
        if action == "gerar_checklist":
            checklist = self.edital_analyzer.checklist(EditalChecklistRequest(**params))
            return checklist.model_dump(mode="json")
        raise HTTPException(status_code=400, detail="ação não suportada")

    def _detect_action(self, pergunta: str) -> str:
        t = pergunta.casefold()
        if "criar" in t and "caso" in t: return "criar_caso"
        if any(x in t for x in ["gerar peça", "gerar peca", "impugnação", "impugnacao", "recurso", "contrarraz"]): return "gerar_peca"
        if "registrar" in t and ("memória" in t or "memoria" in t): return "registrar_memoria"
        if "analisar" in t and "edital" in t: return "analisar_edital"
        if "consultar" in t and ("órgão" in t or "orgao" in t): return "consultar_orgao"
        if "demanda" in t and "consultor" in t: return "criar_demanda_consultor"
        if "checklist" in t: return "gerar_checklist"
        return "gerar_checklist"

    def _normalize_params(self, action: str, params: dict[str, Any], pergunta: str) -> dict[str, Any]:
        out = dict(params or {})
        if action in {"analisar_edital", "gerar_checklist"} and "texto" not in out and len(pergunta) >= 20:
            out["texto"] = pergunta
            out.setdefault("consultar_rag", False)
        if action == "registrar_memoria":
            out.setdefault("tipo", "padrao")
            out.setdefault("titulo", pergunta[:80] or "Memória via Chat")
            out.setdefault("descricao", pergunta or "Registro criado via Chat Actions")
            out.setdefault("fonte", "chat_actions")
        if action == "gerar_peca":
            out.setdefault("tipo_peca", "impugnacao")
            out.setdefault("tese_principal", pergunta[:300])
            out.setdefault("registrar_memoria", False)
        if action == "criar_caso":
            out.setdefault("cliente", "Cliente não informado")
            out.setdefault("modalidade", "")
            out.setdefault("contexto", pergunta)
        return out

    def _missing(self, action: str, p: dict[str, Any]) -> list[str]:
        req = {
            "criar_caso": ["cliente", "orgao", "objeto"],
            "gerar_peca": ["orgao", "objeto", "tese_principal"],
            "registrar_memoria": ["tipo", "titulo", "descricao"],
            "analisar_edital": ["texto"],
            "consultar_orgao": ["nome"],
            "criar_demanda_consultor": ["cliente_id", "tipo", "descricao"],
            "gerar_checklist": ["texto"],
        }[action]
        return [k for k in req if p.get(k) in (None, "", [])]

    def _require_action_permission(self, action: str, user: dict[str, Any]) -> None:
        required = {
            "criar_caso": "casos:escrever",
            "gerar_peca": "documentos:gerar",
            "registrar_memoria": "memoria:escrever",
            "analisar_edital": "dados:ler",
            "consultar_orgao": "orgaos:ler",
            "criar_demanda_consultor": "consultor:escrever",
            "gerar_checklist": "dados:ler",
        }[action]
        if not has_permission(user, required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permissão insuficiente para ação: {required}")

    def _preview_text(self, action: str, p: dict[str, Any], missing: list[str]) -> str:
        base = f"Prévia da ação `{action}`. A LICI não executará nada sem confirmação explícita."
        if missing:
            base += f"\nParâmetros faltantes: {', '.join(missing)}."
        base += "\nParâmetros recebidos:\n" + json.dumps(p, ensure_ascii=False, indent=2, default=str)[:2000]
        return base

    def _target_module(self, action: str) -> str:
        return {
            "criar_caso": "Case Engine", "gerar_peca": "Document Generator", "registrar_memoria": "Memory Core",
            "analisar_edital": "Edital Analyzer", "consultar_orgao": "Órgãos", "criar_demanda_consultor": "Consultor", "gerar_checklist": "Edital Analyzer",
        }[action]

    def _save_request(self, response: ChatActionResponse, user: dict[str, Any], conversa_id: str | None) -> None:
        data = self._read_json()
        record = response.model_dump(mode="json") | {"usuario": self._user(user), "conversa_id": conversa_id, "organization_id": self._org_id(user)}
        data.setdefault("solicitacoes", []).append(record)
        self._write_json(data)
        self._pg_write_request(record)

    def _save_execution(self, record: dict[str, Any], user: dict[str, Any]) -> None:
        data = self._read_json()
        execution = {"id": f"exec_{uuid.uuid4().hex[:12]}", "acao_id": record["acao_id"], "acao": record["acao"], "status": record["status"], "resultado": record.get("resultado"), "erro": record.get("erro", ""), "usuario": self._user(user), "organization_id": self._org_id(user), "criado_em": datetime.now(timezone.utc).isoformat()}
        data.setdefault("execucoes", []).append(execution)
        self._write_json(data)
        self._pg_write_execution(execution)

    def _get_request(self, action_id: str | None) -> dict[str, Any]:
        if not action_id:
            raise HTTPException(status_code=400, detail="acao_id obrigatório")
        for r in self._read_json().get("solicitacoes", []):
            if r.get("acao_id") == action_id:
                return r
        raise HTTPException(status_code=404, detail="ação não encontrada")

    def _update_request(self, record: dict[str, Any]) -> None:
        data = self._read_json()
        items = data.get("solicitacoes", [])
        for idx, item in enumerate(items):
            if item.get("acao_id") == record.get("acao_id"):
                items[idx] = record
                break
        self._write_json(data)
        self._pg_write_request(record)

    def _response_from_record(self, record: dict[str, Any], resultado: dict[str, Any] | None = None) -> ChatActionResponse:
        return ChatActionResponse(**{k: record.get(k) for k in ChatActionResponse.model_fields.keys()} | {"resultado": resultado or record.get("resultado")})

    def _record_action_metric(self, response: ChatActionResponse, user: dict[str, Any], response_time_ms: float, cancelled: bool = False) -> None:
        metric = {"session_id": None, "message_id": response.acao_id, "intent": f"acao:{response.acao}", "tools_used": response.fontes, "success": response.status not in {"erro"}, "found_data": response.status != "erro", "response_time_ms": response_time_ms, "conversation_size": 0, "user_id": user.get("id"), "username": user.get("usuario"), "profile": user.get("perfil"), "operational_profile": user.get("perfil_operacional") or user.get("perfil"), "endpoint": "POST /chat/acao", "errors": [response.erro] if response.erro else [], "question": response.previa[:300], "action_status": response.status, "cancelled": cancelled}
        self.telemetry.record_message(session={"id": f"action_{response.acao_id}", "title": f"Ação {response.acao}", "intent_primary": metric["intent"], "user_id": metric["user_id"], "username": metric["username"], "profile": metric["profile"], "operational_profile": metric["operational_profile"], "status": response.status, "message_count": 1, "created_at": response.criado_em.isoformat(), "updated_at": response.atualizado_em.isoformat()}, message={"id": response.acao_id, "session_id": f"action_{response.acao_id}", "intent": metric["intent"], "question": metric["question"], "answer": response.previa, "found_data": True, "tools_used": response.fontes, "sources": [], "user_id": metric["user_id"], "username": metric["username"], "profile": metric["profile"], "endpoint": "POST /chat/acao", "response_time_ms": response_time_ms, "created_at": response.criado_em.isoformat()}, metric=metric)

    def _can_cancel(self, record: dict[str, Any], user: dict[str, Any]) -> bool:
        permissions = set(user.get("permissoes") or [])
        if not self._same_org(record, user):
            details = {"acao_id": record.get("acao_id"), "organization_id": self._org_id(user), "record_organization_id": record.get("organization_id"), "motivo": "cancelamento_cross_org_negado"}
            audit_event("chat_actions", "tentativa_cancelamento_cross_org_negada", "erro", details, record.get("acao_id"))
            return False
        if user.get("perfil") == "admin" or "auth:admin" in permissions or "*" in permissions:
            return True
        owner = record.get("usuario") or {}
        return bool(user.get("id") and owner.get("id") == user.get("id"))

    def _record_security_metric(self, record: dict[str, Any], user: dict[str, Any], reason: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        action_id = record.get("acao_id") or f"act_unknown_{uuid.uuid4().hex[:8]}"
        metric = {
            "session_id": None,
            "message_id": action_id,
            "intent": "security:chat_action_cancel_forbidden",
            "tools_used": ["Chat Actions", "Security"],
            "success": False,
            "found_data": False,
            "response_time_ms": 0,
            "conversation_size": 0,
            "user_id": user.get("id"),
            "username": user.get("usuario"),
            "profile": user.get("perfil"),
            "operational_profile": user.get("perfil_operacional") or user.get("perfil"),
            "endpoint": "POST /chat/acao",
            "errors": [reason],
            "question": f"Tentativa negada de cancelar ação {action_id}",
            "action_status": "forbidden",
            "security_event": reason,
        }
        self.telemetry.record_message(
            session={"id": f"security_{action_id}", "title": "Tentativa negada de cancelamento", "intent_primary": metric["intent"], "user_id": metric["user_id"], "username": metric["username"], "profile": metric["profile"], "operational_profile": metric["operational_profile"], "status": "forbidden", "message_count": 1, "created_at": now, "updated_at": now},
            message={"id": f"sec_{uuid.uuid4().hex[:12]}", "session_id": f"security_{action_id}", "intent": metric["intent"], "question": metric["question"], "answer": reason, "found_data": False, "tools_used": metric["tools_used"], "sources": [], "user_id": metric["user_id"], "username": metric["username"], "profile": metric["profile"], "endpoint": "POST /chat/acao", "response_time_ms": 0, "created_at": now},
            metric=metric,
        )

    def _user(self, user: dict[str, Any]) -> dict[str, Any]:
        return {"id": user.get("id"), "usuario": user.get("usuario"), "perfil": user.get("perfil"), "perfil_operacional": user.get("perfil_operacional"), "organization_id": self._org_id(user)}

    def _org_id(self, user: dict[str, Any]) -> str:
        return user.get("active_organization_id") or user.get("organization_id") or "default-org"

    def _same_org(self, record: dict[str, Any], user: dict[str, Any]) -> bool:
        return (record.get("organization_id") or "default-org") == self._org_id(user)

    def _read_json(self) -> dict[str, Any]:
        try: return json.loads(ACTIONS_PATH.read_text(encoding="utf-8"))
        except Exception: return {"solicitacoes": [], "execucoes": []}

    def _write_json(self, data: dict[str, Any]) -> None:
        with NamedTemporaryFile("w", encoding="utf-8", dir=CHAT_ROOT, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2, default=str); tmp.write("\n"); tmp_path = Path(tmp.name)
        tmp_path.replace(ACTIONS_PATH)

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith("LICI_DATABASE_URL="): return line.split("=", 1)[1].strip().strip('"').strip("'")
        except FileNotFoundError: return None
        return None

    def _pg_available(self) -> bool:
        return bool(psycopg and self.dsn)

    def _ensure_pg(self) -> None:
        if not self._pg_available(): return
        try:
            with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("""CREATE TABLE IF NOT EXISTS chat_action_requests (id TEXT PRIMARY KEY, action_type TEXT, status TEXT, parameters JSONB, preview TEXT, user_id TEXT, username TEXT, organization_id TEXT DEFAULT 'default-org', raw_payload JSONB, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)""")
                    cur.execute("""ALTER TABLE chat_action_requests ADD COLUMN IF NOT EXISTS organization_id TEXT DEFAULT 'default-org'""")
                    cur.execute("""CREATE TABLE IF NOT EXISTS chat_action_executions (id TEXT PRIMARY KEY, request_id TEXT, action_type TEXT, status TEXT, result JSONB, error TEXT, user_id TEXT, username TEXT, organization_id TEXT DEFAULT 'default-org', raw_payload JSONB, created_at TIMESTAMPTZ)""")
                    cur.execute("""ALTER TABLE chat_action_executions ADD COLUMN IF NOT EXISTS organization_id TEXT DEFAULT 'default-org'""")
        except Exception as exc:
            structured_log("api", "chat_actions_postgres_unavailable", "alerta", {"erro": str(exc)})

    def _pg_write_request(self, r: dict[str, Any]) -> None:
        if not self._pg_available(): return
        try:
            self._ensure_pg()
            with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    u = r.get("usuario") or {}
                    cur.execute("""INSERT INTO chat_action_requests (id,action_type,status,parameters,preview,user_id,username,organization_id,raw_payload,created_at,updated_at) VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s::jsonb,%s,%s) ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status, parameters=EXCLUDED.parameters, preview=EXCLUDED.preview, organization_id=EXCLUDED.organization_id, raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at""", (r["acao_id"], r["acao"], r["status"], json.dumps(r.get("parametros", {}), ensure_ascii=False), r.get("previa"), u.get("id"), u.get("usuario"), r.get("organization_id") or "default-org", json.dumps(r, ensure_ascii=False, default=str), r.get("criado_em"), r.get("atualizado_em")))
        except Exception as exc:
            audit_event("chat_actions", "falha_postgres_acao", "erro", {"erro": str(exc)}, r.get("acao_id"))

    def _pg_write_execution(self, e: dict[str, Any]) -> None:
        if not self._pg_available(): return
        try:
            self._ensure_pg()
            with psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    u = e.get("usuario") or {}
                    cur.execute("""INSERT INTO chat_action_executions (id,request_id,action_type,status,result,error,user_id,username,organization_id,raw_payload,created_at) VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT (id) DO NOTHING""", (e["id"], e["acao_id"], e["acao"], e["status"], json.dumps(e.get("resultado"), ensure_ascii=False, default=str), e.get("erro", ""), u.get("id"), u.get("usuario"), e.get("organization_id") or "default-org", json.dumps(e, ensure_ascii=False, default=str), e.get("criado_em")))
        except Exception as exc:
            audit_event("chat_actions", "falha_postgres_execucao", "erro", {"erro": str(exc)}, e.get("acao_id"))
