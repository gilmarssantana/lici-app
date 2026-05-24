from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Literal
from uuid import uuid4

from fastapi import HTTPException, status

from app.services.audit_log import audit_event

ORG_ROOT = Path("/root/lici-app/organizations")
ORGS_FILE = ORG_ROOT / "organizations.json"
ORG_USERS_FILE = ORG_ROOT / "organization_users.json"
DEFAULT_ORG_ID = "default-org"

OrgRole = Literal["admin_global", "admin_org", "operador", "leitura"]
LEGACY_PROFILE_TO_ORG_ROLE = {
    "admin": "admin_global",
    "consultor": "operador",
    "fornecedor": "operador",
    "comprador": "operador",
    "leitura": "leitura",
}
ORG_ROLE_PERMISSIONS = {
    "admin_global": ["*", "org:admin_global", "org:admin", "org:trocar", "org:ler", "org:escrever"],
    "admin_org": ["org:admin", "org:trocar", "org:ler", "org:escrever", "usuarios:gerenciar_org"],
    "operador": ["org:trocar", "org:ler", "dados:ler", "dados:escrever"],
    "leitura": ["org:trocar", "org:ler", "dados:ler"],
}


class JsonOrganizationStore:
    """JSON-first store for multi-organization Fase 1.

    Keeps the current single-org deployment working by creating a default
    organization and placing legacy users there when they have no explicit
    organization metadata yet.
    """

    def __init__(self, root: Path | str = ORG_ROOT):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.orgs_path = self.root / "organizations.json"
        self.memberships_path = self.root / "organization_users.json"
        if not self.orgs_path.exists():
            self._write_json(self.orgs_path, [self._default_org()])
        if not self.memberships_path.exists():
            self._write_json(self.memberships_path, [])

    def ensure_default_org(self) -> dict[str, Any]:
        orgs = self.list_organizations(include_inactive=True)
        existing = next((org for org in orgs if org.get("id") == DEFAULT_ORG_ID), None)
        if existing:
            return existing
        org = self._default_org()
        orgs.append(org)
        self._write_json(self.orgs_path, orgs)
        return org

    def list_organizations(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        orgs = self._read_json(self.orgs_path, [])
        if include_inactive:
            return orgs
        return [org for org in orgs if org.get("status", "ativa") == "ativa"]

    def get_organization(self, organization_id: str | None) -> dict[str, Any] | None:
        org_id = organization_id or DEFAULT_ORG_ID
        return next((org for org in self.list_organizations(include_inactive=True) if org.get("id") == org_id), None)

    def create_organization(self, nome: str, slug: str | None = None, actor: dict[str, Any] | None = None) -> dict[str, Any]:
        orgs = self.list_organizations(include_inactive=True)
        normalized_slug = (slug or nome).strip().lower().replace(" ", "-")
        if any(org.get("slug") == normalized_slug for org in orgs):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Organização já existe")
        now = _now_iso()
        org = {
            "id": str(uuid4()),
            "nome": nome.strip(),
            "slug": normalized_slug,
            "status": "ativa",
            "criado_em": now,
            "atualizado_em": now,
        }
        orgs.append(org)
        self._write_json(self.orgs_path, orgs)
        audit_event("organizacoes", "criar_organizacao", "ok", {"organization_id": org["id"], "ator": actor_label(actor)}, org["id"])
        return org

    def list_memberships(self, user_id: str | None = None, organization_id: str | None = None) -> list[dict[str, Any]]:
        memberships = self._read_json(self.memberships_path, [])
        if user_id:
            memberships = [item for item in memberships if item.get("user_id") == user_id]
        if organization_id:
            memberships = [item for item in memberships if item.get("organization_id") == organization_id]
        return memberships

    def upsert_membership(self, user_id: str, organization_id: str, role: OrgRole = "operador", actor: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.get_organization(organization_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organização não encontrada")
        memberships = self._read_json(self.memberships_path, [])
        now = _now_iso()
        for item in memberships:
            if item.get("user_id") == user_id and item.get("organization_id") == organization_id:
                item.update({"role": role, "status": "ativo", "atualizado_em": now})
                self._write_json(self.memberships_path, memberships)
                audit_event("organizacoes", "alterar_usuario_organizacao", "ok", {"user_id": user_id, "organization_id": organization_id, "role": role, "ator": actor_label(actor)}, user_id)
                return item
        item = {
            "id": str(uuid4()),
            "organization_id": organization_id,
            "user_id": user_id,
            "role": role,
            "status": "ativo",
            "criado_em": now,
            "atualizado_em": now,
        }
        memberships.append(item)
        self._write_json(self.memberships_path, memberships)
        audit_event("organizacoes", "vincular_usuario_organizacao", "ok", {"user_id": user_id, "organization_id": organization_id, "role": role, "ator": actor_label(actor)}, user_id)
        return item

    def ensure_user_membership(self, user: dict[str, Any]) -> dict[str, Any]:
        self.ensure_default_org()
        user_id = str(user.get("id"))
        memberships = [m for m in self.list_memberships(user_id=user_id) if m.get("status") == "ativo"]
        if memberships:
            return self.enrich_user(user)
        role = LEGACY_PROFILE_TO_ORG_ROLE.get(user.get("perfil"), "operador")
        self.upsert_membership(user_id, DEFAULT_ORG_ID, role)  # legacy fallback
        return self.enrich_user(user)

    def enrich_user(self, user: dict[str, Any]) -> dict[str, Any]:
        result = dict(user)
        memberships = [m for m in self.list_memberships(user_id=str(user.get("id"))) if m.get("status") == "ativo"]
        if not memberships:
            memberships = [self.upsert_membership(str(user.get("id")), DEFAULT_ORG_ID, LEGACY_PROFILE_TO_ORG_ROLE.get(user.get("perfil"), "operador"))]
        orgs = []
        for membership in memberships:
            org = self.get_organization(membership.get("organization_id")) or self.ensure_default_org()
            orgs.append({**org, "role": membership.get("role", "operador")})
        active = result.get("active_organization_id") or result.get("organization_id") or orgs[0]["id"]
        if active not in {org["id"] for org in orgs} and result.get("perfil") != "admin":
            active = orgs[0]["id"]
        result["organization_id"] = active
        result["active_organization_id"] = active
        result["organizations"] = orgs
        result["organization_ids"] = [org["id"] for org in orgs]
        result["organization_role"] = self.role_for_user(result, active)
        result["organization_permissions"] = ORG_ROLE_PERMISSIONS.get(result["organization_role"], [])
        return result

    def role_for_user(self, user: dict[str, Any], organization_id: str | None = None) -> str:
        if user.get("perfil") == "admin" or "*" in set(user.get("permissoes") or []):
            return "admin_global"
        org_id = organization_id or user.get("active_organization_id") or user.get("organization_id") or DEFAULT_ORG_ID
        membership = next((m for m in self.list_memberships(user_id=str(user.get("id")), organization_id=org_id) if m.get("status") == "ativo"), None)
        return (membership or {}).get("role", LEGACY_PROFILE_TO_ORG_ROLE.get(user.get("perfil"), "operador"))

    def assert_access(self, user: dict[str, Any], organization_id: str | None, action: str = "acessar") -> str:
        org_id = organization_id or user.get("active_organization_id") or user.get("organization_id") or DEFAULT_ORG_ID
        enriched = self.enrich_user(user)
        if enriched.get("perfil") == "admin" or "*" in set(enriched.get("permissoes") or []):
            return org_id
        if org_id in set(enriched.get("organization_ids") or []):
            return org_id
        audit_event(
            "security",
            "acesso_negado_cross_org",
            "erro",
            {"motivo": "organizacao_fora_do_escopo", "acao": action, "usuario": enriched.get("usuario"), "requested_organization_id": org_id, "allowed_organization_ids": enriched.get("organization_ids", [])},
            enriched.get("id"),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: organização fora do escopo do usuário")

    def switch_active_organization(self, user: dict[str, Any], organization_id: str) -> dict[str, Any]:
        org_id = self.assert_access(user, organization_id, action="trocar_organizacao")
        enriched = self.enrich_user(user)
        enriched["organization_id"] = org_id
        enriched["active_organization_id"] = org_id
        enriched["organization_role"] = self.role_for_user(enriched, org_id)
        audit_event("organizacoes", "trocar_organizacao", "ok", {"usuario": enriched.get("usuario"), "organization_id": org_id}, enriched.get("id"))
        return enriched

    def active_users(self) -> list[dict[str, Any]]:
        # Fase 1 approximation: active memberships by organization. Real online status comes in later via sessions/heartbeat.
        memberships = [m for m in self.list_memberships() if m.get("status") == "ativo"]
        return memberships

    def _default_org(self) -> dict[str, Any]:
        now = _now_iso()
        return {
            "id": DEFAULT_ORG_ID,
            "nome": os.getenv("LICI_DEFAULT_ORG_NAME", "Organização Principal"),
            "slug": "default",
            "status": "ativa",
            "criado_em": now,
            "atualizado_em": now,
            "fallback_single_org": True,
        }

    def _read_json(self, path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2, default=str)
            tmp.write("\n")
            tmp_path = Path(tmp.name)
        os.chmod(tmp_path, 0o600)
        tmp_path.replace(path)


def actor_label(actor: dict[str, Any] | None) -> str:
    return (actor or {}).get("usuario") or "sistema"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
