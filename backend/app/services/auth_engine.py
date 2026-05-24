from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.schemas.auth import AuthChangeProfileRequest, AuthLoginRequest, AuthUserCreateRequest, UserProfile
from app.services.audit_log import audit_event
from app.services.auth_pg_store import PostgresAuthStore
from app.services.auth_store import JsonAuthStore
from app.services.organization import DEFAULT_ORG_ID, JsonOrganizationStore, LEGACY_PROFILE_TO_ORG_ROLE

JWT_HEADER = {"alg": "HS256", "typ": "JWT"}

PROFILE_TO_OPERATIONAL = {
    "admin": "fornecedor",
    "consultor": "consultor",
    "fornecedor": "fornecedor",
    "comprador": "comprador",
    "leitura": "fornecedor",
}

DEFAULT_PERMISSIONS = {
    "admin": ["*", "auth:admin", "usuarios:gerenciar", "perfil:selecionar", "dados:ler", "dados:escrever", "audit:ler", "org:admin_global", "org:admin", "org:ler", "org:escrever", "org:trocar"],
    "consultor": ["dados:ler", "casos:ler", "casos:escrever", "consultor:ler", "consultor:escrever", "upload:ler", "upload:escrever", "documentos:ler", "documentos:gerar", "export:ler", "memoria:ler", "memoria:escrever"],
    "fornecedor": ["dados:ler", "radar:ler", "radar:escrever", "casos:ler", "casos:escrever", "upload:ler", "upload:escrever", "documentos:ler", "documentos:gerar", "export:ler", "memoria:ler", "memoria:escrever"],
    "comprador": ["dados:ler", "comprador:operar", "orgaos:ler", "orgaos:escrever", "casos:ler", "casos:escrever", "documentos:ler", "documentos:gerar", "export:ler", "memoria:ler"],
    "leitura": ["dados:ler", "org:ler", "org:trocar"],
}


class LiciAuthEngine:
    def __init__(self, store: JsonAuthStore | None = None, pg_store: PostgresAuthStore | None = None):
        self.store = store or JsonAuthStore()
        self.pg_store = pg_store or PostgresAuthStore()
        self.org_store = JsonOrganizationStore()

    def login(self, payload: AuthLoginRequest) -> dict[str, Any]:
        user = self._find_by_username(payload.usuario)
        if not user or user.get("status") != "ativo" or not self._verify_password(payload.senha, user.get("senha_hash", "")):
            audit_event("auth", "login", "erro", {"usuario": payload.usuario, "motivo": "credenciais_invalidas"})
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário ou senha inválidos")

        now = _now()
        user["ultimo_login_em"] = now.isoformat()
        user["atualizado_em"] = now.isoformat()
        self._upsert_user(user)

        token, expires_in = self._create_access_token(user)
        audit_event("auth", "login", "ok", {"usuario": user["usuario"], "perfil": user["perfil"]}, user["id"])
        return {"access_token": token, "token_type": "bearer", "expires_in": expires_in, "usuario": self.public_user(user)}

    def me(self, token: str) -> dict[str, Any]:
        user = self.user_from_token(token)
        return {"usuario": self.public_user(user)}

    def list_users(self) -> dict[str, Any]:
        users = [self.public_user(user) for user in self._list_users()]
        return {"usuarios": users, "total": len(users)}

    def create_user(self, payload: AuthUserCreateRequest, actor: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._find_by_username(payload.usuario):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Usuário já existe")
        now = _now().isoformat()
        organization_id = payload.organization_id or DEFAULT_ORG_ID
        self.org_store.ensure_default_org()
        user = {
            "id": str(uuid4()),
            "usuario": payload.usuario.strip().lower(),
            "nome": payload.nome.strip(),
            "senha_hash": self._hash_password(payload.senha),
            "perfil": payload.perfil,
            "perfil_operacional": PROFILE_TO_OPERATIONAL[payload.perfil],
            "permissoes": payload.permissoes or DEFAULT_PERMISSIONS[payload.perfil],
            "status": "ativo",
            "organization_id": organization_id,
            "active_organization_id": organization_id,
            "criado_em": now,
            "atualizado_em": now,
            "ultimo_login_em": None,
        }
        self._upsert_user(user)
        self.org_store.upsert_membership(
            user["id"],
            organization_id,
            payload.organization_role or LEGACY_PROFILE_TO_ORG_ROLE.get(payload.perfil, "operador"),
            actor=actor,
        )
        audit_event(
            "auth",
            "criar_usuario",
            "ok",
            {"usuario": user["usuario"], "perfil": user["perfil"], "ator": actor.get("usuario") if actor else "bootstrap"},
            user["id"],
        )
        return self.public_user(user)

    def change_profile(self, user_id: str, payload: AuthChangeProfileRequest, actor: dict[str, Any]) -> dict[str, Any]:
        user = self._find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
        user["perfil"] = payload.perfil
        user["perfil_operacional"] = PROFILE_TO_OPERATIONAL[payload.perfil]
        user["permissoes"] = payload.permissoes or DEFAULT_PERMISSIONS[payload.perfil]
        user["atualizado_em"] = _now().isoformat()
        self._upsert_user(user)
        audit_event("auth", "alterar_perfil", "ok", {"usuario": user["usuario"], "perfil": user["perfil"], "ator": actor["usuario"]}, user["id"])
        return self.public_user(user)

    def deactivate_user(self, user_id: str, actor: dict[str, Any]) -> dict[str, Any]:
        user = self._find_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
        if user.get("id") == actor.get("id"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não é permitido desativar o próprio usuário")
        user["status"] = "inativo"
        user["atualizado_em"] = _now().isoformat()
        self._upsert_user(user)
        audit_event("auth", "desativar_usuario", "ok", {"usuario": user["usuario"], "ator": actor["usuario"]}, user["id"])
        return self.public_user(user)

    def user_from_token(self, token: str) -> dict[str, Any]:
        payload = self._decode_token(token)
        user_id = payload.get("sub")
        user = self._find_by_id(str(user_id)) if user_id else None
        if not user or user.get("status") != "ativo":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou usuário inativo")
        return user

    def require_admin(self, user: dict[str, Any]) -> None:
        if user.get("perfil") != "admin" and "auth:admin" not in user.get("permissoes", []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão de administrador necessária")

    def public_user(self, user: dict[str, Any]) -> dict[str, Any]:
        enriched = self.org_store.ensure_user_membership(user)
        return {k: v for k, v in enriched.items() if k != "senha_hash"}

    def bootstrap_allowed(self) -> bool:
        return len(self._list_users()) == 0

    def _list_users(self) -> list[dict[str, Any]]:
        try:
            if self.pg_store.available():
                return self.pg_store.list_users()
        except Exception as exc:
            audit_event("auth", "postgres_fallback_json", "erro", {"operacao": "list_users", "erro": str(exc)})
        return self.store.list_users()

    def _find_by_username(self, username: str) -> dict[str, Any] | None:
        try:
            if self.pg_store.available():
                user = self.pg_store.find_by_username(username)
                if user:
                    return user
        except Exception as exc:
            audit_event("auth", "postgres_fallback_json", "erro", {"operacao": "find_by_username", "erro": str(exc)})
        return self.store.find_by_username(username)

    def _find_by_id(self, user_id: str) -> dict[str, Any] | None:
        try:
            if self.pg_store.available():
                user = self.pg_store.find_by_id(user_id)
                if user:
                    return user
        except Exception as exc:
            audit_event("auth", "postgres_fallback_json", "erro", {"operacao": "find_by_id", "erro": str(exc)})
        return self.store.find_by_id(user_id)

    def _upsert_user(self, user: dict[str, Any]) -> dict[str, Any]:
        # JSON remains mandatory fallback and compatibility snapshot.
        self.store.upsert_user(user)
        try:
            if self.pg_store.available():
                self.pg_store.upsert_user(user)
                audit_event("auth", "dual_write_postgres", "ok", {"usuario": user.get("usuario")}, user.get("id"))
            else:
                audit_event("auth", "dual_write_postgres", "erro", {"usuario": user.get("usuario"), "motivo": "postgres_indisponivel"}, user.get("id"))
        except Exception as exc:
            audit_event("auth", "dual_write_postgres", "erro", {"usuario": user.get("usuario"), "erro": str(exc)}, user.get("id"))
        return user

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        iterations = 210_000
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return f"pbkdf2_sha256${iterations}${_b64url(salt)}${_b64url(digest)}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations_raw, salt_raw, digest_raw = password_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            iterations = int(iterations_raw)
            salt = _b64url_decode(salt_raw)
            expected = _b64url_decode(digest_raw)
            actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False

    def _create_access_token(self, user: dict[str, Any]) -> tuple[str, int]:
        config = self.store.config()
        expires_in = int(config.get("access_token_expire_minutes", 480)) * 60
        now = _now()
        enriched = self.org_store.ensure_user_membership(user)
        payload = {
            "sub": user["id"],
            "usuario": user["usuario"],
            "perfil": user["perfil"],
            "perfil_operacional": user["perfil_operacional"],
            "organization_id": enriched.get("active_organization_id") or DEFAULT_ORG_ID,
            "organization_ids": enriched.get("organization_ids", [DEFAULT_ORG_ID]),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        }
        return self._encode_token(payload), expires_in

    def _encode_token(self, payload: dict[str, Any]) -> str:
        header = _b64url_json(JWT_HEADER)
        body = _b64url_json(payload)
        signature = hmac.new(self.store.config()["jwt_secret"].encode("utf-8"), f"{header}.{body}".encode("utf-8"), hashlib.sha256).digest()
        return f"{header}.{body}.{_b64url(signature)}"

    def _decode_token(self, token: str) -> dict[str, Any]:
        try:
            header_raw, body_raw, sig_raw = token.split(".", 2)
            expected = hmac.new(self.store.config()["jwt_secret"].encode("utf-8"), f"{header_raw}.{body_raw}".encode("utf-8"), hashlib.sha256).digest()
            if not hmac.compare_digest(_b64url(expected), sig_raw):
                raise ValueError("invalid signature")
            payload = json.loads(_b64url_decode(body_raw))
            if int(payload.get("exp", 0)) < int(_now().timestamp()):
                raise ValueError("expired")
            return payload
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _b64url_json(data: dict[str, Any]) -> str:
    return _b64url(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
