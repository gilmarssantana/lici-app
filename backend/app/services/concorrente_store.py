from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.schemas.concorrente import ConcorrenteEvent, ConcorrenteRecord
from app.services.audit_log import audit_event
from app.services.concorrente_pg_store import PostgresConcorrenteStore


class JsonConcorrenteStore:
    def __init__(self, root: Path | str = '/root/lici-app/concorrentes'):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.concorrentes_path = self.root / 'concorrentes.json'
        self.historico_path = self.root / 'historico.json'
        if not self.concorrentes_path.exists():
            self._write_json(self.concorrentes_path, [])
        if not self.historico_path.exists():
            self._write_json(self.historico_path, [])

    def list(self, organization_id: str | None = None) -> list[ConcorrenteRecord]:
        items = self._read_concorrentes()
        if organization_id:
            items = [item for item in items if (item.organization_id or "default-org") == organization_id]
        return sorted(items, key=lambda item: item.atualizado_em, reverse=True)

    def get(self, concorrente_id: str, organization_id: str | None = None) -> ConcorrenteRecord | None:
        for item in self._read_concorrentes():
            if item.id == concorrente_id and (organization_id is None or (item.organization_id or "default-org") == organization_id):
                return item
        return None

    def find_by_nome_cnpj(self, nome: str, cnpj: str = '') -> ConcorrenteRecord | None:
        cnpj_norm = self._only_digits(cnpj)
        nome_norm = self._norm(nome)
        for item in self._read_concorrentes():
            if cnpj_norm and self._only_digits(item.cnpj) == cnpj_norm:
                return item
            if self._norm(item.nome) == nome_norm:
                return item
        return None

    def upsert(self, concorrente: ConcorrenteRecord) -> ConcorrenteRecord:
        items = self._read_concorrentes()
        for idx, item in enumerate(items):
            if item.id == concorrente.id:
                items[idx] = concorrente
                self._write_concorrentes(items)
                return concorrente
        items.append(concorrente)
        self._write_concorrentes(items)
        return concorrente

    def add_event(self, event: ConcorrenteEvent) -> ConcorrenteEvent:
        events = self._read_eventos()
        events.append(event)
        self._write_eventos(events)
        return event

    def history(self, concorrente_id: str) -> list[ConcorrenteEvent]:
        return sorted([e for e in self._read_eventos() if e.concorrente_id == concorrente_id], key=lambda item: item.data, reverse=True)

    def events(self) -> list[ConcorrenteEvent]:
        return sorted(self._read_eventos(), key=lambda item: item.data, reverse=True)

    def _read_concorrentes(self) -> list[ConcorrenteRecord]:
        raw = json.loads(self.concorrentes_path.read_text(encoding='utf-8'))
        return [ConcorrenteRecord(**item) for item in raw]

    def _read_eventos(self) -> list[ConcorrenteEvent]:
        raw = json.loads(self.historico_path.read_text(encoding='utf-8'))
        return [ConcorrenteEvent(**item) for item in raw]

    def _write_concorrentes(self, items: list[ConcorrenteRecord]) -> None:
        self._write_json(self.concorrentes_path, [item.model_dump() for item in items])

    def _write_eventos(self, items: list[ConcorrenteEvent]) -> None:
        self._write_json(self.historico_path, [item.model_dump() for item in items])

    def _write_json(self, path: Path, data: list[dict]) -> None:
        with NamedTemporaryFile('w', encoding='utf-8', dir=self.root, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2, default=str)
            tmp.write('\n')
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)

    def _norm(self, value: str) -> str:
        return ' '.join((value or '').strip().lower().split())

    def _only_digits(self, value: str) -> str:
        return ''.join(ch for ch in (value or '') if ch.isdigit())


class HybridConcorrenteStore:
    """Concorrentes dual-read/dual-write: PostgreSQL primeiro; JSON fallback; JSON obrigatório na escrita."""

    def __init__(self, json_store: JsonConcorrenteStore | None = None, pg_store: PostgresConcorrenteStore | None = None):
        self.json_store = json_store or JsonConcorrenteStore()
        self.pg_store = pg_store or PostgresConcorrenteStore()

    def list(self, organization_id: str | None = None) -> list[ConcorrenteRecord]:
        try:
            if self.pg_store.available():
                items = self.pg_store.list()
                if organization_id:
                    items = [item for item in items if (item.organization_id or "default-org") == organization_id]
                return items
            audit_event('concorrentes_engine', 'postgres_fallback_json', 'erro', {'operacao': 'list', 'motivo': 'postgres_indisponivel'})
        except Exception as exc:
            audit_event('concorrentes_engine', 'postgres_fallback_json', 'erro', {'operacao': 'list', 'erro': str(exc)})
        return self.json_store.list(organization_id=organization_id)

    def get(self, concorrente_id: str, organization_id: str | None = None) -> ConcorrenteRecord | None:
        try:
            if self.pg_store.available():
                item = self.pg_store.get(concorrente_id)
                if item and (organization_id is None or (item.organization_id or "default-org") == organization_id):
                    return item
                return None
            audit_event('concorrentes_engine', 'postgres_fallback_json', 'erro', {'operacao': 'get', 'motivo': 'postgres_indisponivel', 'concorrente_id': concorrente_id}, concorrente_id)
        except Exception as exc:
            audit_event('concorrentes_engine', 'postgres_fallback_json', 'erro', {'operacao': 'get', 'concorrente_id': concorrente_id, 'erro': str(exc)}, concorrente_id)
        return self.json_store.get(concorrente_id, organization_id=organization_id)

    def find_by_nome_cnpj(self, nome: str, cnpj: str = '') -> ConcorrenteRecord | None:
        try:
            if self.pg_store.available():
                return self.pg_store.find_by_nome_cnpj(nome, cnpj)
        except Exception as exc:
            audit_event('concorrentes_engine', 'postgres_fallback_json', 'erro', {'operacao': 'find_by_nome_cnpj', 'erro': str(exc)})
        return self.json_store.find_by_nome_cnpj(nome, cnpj)

    def upsert(self, concorrente: ConcorrenteRecord) -> ConcorrenteRecord:
        saved = self.json_store.upsert(concorrente)
        try:
            if self.pg_store.available():
                self.pg_store.upsert(saved)
                audit_event('concorrentes_engine', 'dual_write_postgres', 'ok', {'operacao': 'upsert'}, saved.id)
            else:
                audit_event('concorrentes_engine', 'dual_write_postgres', 'erro', {'operacao': 'upsert', 'motivo': 'postgres_indisponivel'}, saved.id)
        except Exception as exc:
            audit_event('concorrentes_engine', 'dual_write_postgres', 'erro', {'operacao': 'upsert', 'erro': str(exc)}, saved.id)
        return saved

    def add_event(self, event: ConcorrenteEvent) -> ConcorrenteEvent:
        saved = self.json_store.add_event(event)
        try:
            if self.pg_store.available():
                self.pg_store.add_event(saved)
                audit_event('concorrentes_engine', 'dual_write_postgres', 'ok', {'operacao': 'add_event'}, saved.id)
            else:
                audit_event('concorrentes_engine', 'dual_write_postgres', 'erro', {'operacao': 'add_event', 'motivo': 'postgres_indisponivel'}, saved.id)
        except Exception as exc:
            audit_event('concorrentes_engine', 'dual_write_postgres', 'erro', {'operacao': 'add_event', 'erro': str(exc)}, saved.id)
        return saved

    def history(self, concorrente_id: str) -> list[ConcorrenteEvent]:
        try:
            if self.pg_store.available():
                return self.pg_store.history(concorrente_id)
        except Exception as exc:
            audit_event('concorrentes_engine', 'postgres_fallback_json', 'erro', {'operacao': 'history', 'concorrente_id': concorrente_id, 'erro': str(exc)}, concorrente_id)
        return self.json_store.history(concorrente_id)

    def events(self) -> list[ConcorrenteEvent]:
        try:
            if self.pg_store.available():
                return self.pg_store.events()
        except Exception as exc:
            audit_event('concorrentes_engine', 'postgres_fallback_json', 'erro', {'operacao': 'events', 'erro': str(exc)})
        return self.json_store.events()
