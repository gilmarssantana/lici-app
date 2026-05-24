from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone

from app.schemas.document_generator import GeneratedDocumentRecord
from app.schemas.upload import UploadDocumentRecord

try:
    import psycopg
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    psycopg = None
    dict_row = None

POSTGRES_ENV_FILE = Path("/root/lici-app/secrets/postgres.env")


class _BasePostgresStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.getenv("LICI_DATABASE_URL") or self._dsn_from_env_file()

    def available(self) -> bool:
        if not psycopg or not self.dsn:
            return False
        try:
            with psycopg.connect(self.dsn, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True
        except Exception:
            return False

    def _connect(self):
        if not psycopg or not self.dsn:
            raise RuntimeError("PostgreSQL indisponível")
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=3)

    def _dsn_from_env_file(self) -> str | None:
        try:
            for line in POSTGRES_ENV_FILE.read_text(encoding="utf-8").splitlines():
                if line.startswith("LICI_DATABASE_URL="):
                    return line.split("=", 1)[1].strip()
        except FileNotFoundError:
            return None
        return None

    def _raw(self, raw: Any) -> dict[str, Any]:
        if raw is None:
            return {}
        if isinstance(raw, str):
            return json.loads(raw)
        return raw


class PostgresUploadDocumentStore(_BasePostgresStore):
    def list(self) -> list[UploadDocumentRecord]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM uploaded_documents ORDER BY updated_at DESC NULLS LAST, created_at DESC")
                return [UploadDocumentRecord(**self._raw(row["raw_payload"])) for row in cur.fetchall()]

    def get(self, document_id: str) -> UploadDocumentRecord | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM uploaded_documents WHERE id = %s", (document_id,))
                row = cur.fetchone()
                return UploadDocumentRecord(**self._raw(row["raw_payload"])) if row else None

    def create(self, record: UploadDocumentRecord) -> UploadDocumentRecord:
        return self.upsert(record)

    def update(self, record: UploadDocumentRecord) -> UploadDocumentRecord:
        return self.upsert(record)

    def upsert(self, record: UploadDocumentRecord) -> UploadDocumentRecord:
        raw = record.model_dump(mode="json")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO uploaded_documents (
                      id, original_name, stored_name, file_path, content_type, extension, size_bytes,
                      status, extracted_chars, case_id, raw_payload, created_at, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      original_name=EXCLUDED.original_name, stored_name=EXCLUDED.stored_name,
                      file_path=EXCLUDED.file_path, content_type=EXCLUDED.content_type, extension=EXCLUDED.extension,
                      size_bytes=EXCLUDED.size_bytes, status=EXCLUDED.status, extracted_chars=EXCLUDED.extracted_chars,
                      case_id=EXCLUDED.case_id, raw_payload=EXCLUDED.raw_payload, updated_at=EXCLUDED.updated_at
                    """,
                    (record.id, record.nome_original, record.nome_arquivo, record.caminho, record.content_type,
                     record.extensao, record.tamanho_bytes, record.status, record.caracteres_extraidos, record.caso_id,
                     json.dumps(raw, ensure_ascii=False, default=str), record.criado_em, record.atualizado_em),
                )
        return record


class PostgresGeneratedDocumentStore(_BasePostgresStore):
    def list(self) -> list[GeneratedDocumentRecord]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM generated_documents ORDER BY created_at DESC")
                return [self._record_from_raw(row["raw_payload"]) for row in cur.fetchall()]

    def create(self, record: GeneratedDocumentRecord) -> GeneratedDocumentRecord:
        return self.upsert(record)

    def upsert(self, record: GeneratedDocumentRecord) -> GeneratedDocumentRecord:
        raw = record.model_dump(mode="json")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO generated_documents (
                      id, document_type, title, file_name, file_path, client_name, orgao_name, process,
                      modality, object, case_id, uploaded_document_id, base_decision, base_score,
                      raw_payload, created_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      document_type=EXCLUDED.document_type, title=EXCLUDED.title, file_name=EXCLUDED.file_name,
                      file_path=EXCLUDED.file_path, client_name=EXCLUDED.client_name, orgao_name=EXCLUDED.orgao_name,
                      process=EXCLUDED.process, modality=EXCLUDED.modality, object=EXCLUDED.object,
                      case_id=EXCLUDED.case_id, uploaded_document_id=EXCLUDED.uploaded_document_id,
                      base_decision=EXCLUDED.base_decision, base_score=EXCLUDED.base_score, raw_payload=EXCLUDED.raw_payload
                    """,
                    (record.id, record.tipo, record.titulo, record.arquivo, record.caminho, record.cliente,
                     record.orgao, record.processo, record.modalidade, record.objeto, record.case_id,
                     record.documento_id, record.decisao_base, record.score_base,
                     json.dumps(raw, ensure_ascii=False, default=str), record.criado_em),
                )
        return record

    def _record_from_raw(self, raw: Any) -> GeneratedDocumentRecord:
        data = self._raw(raw)
        if not data.get("texto") and data.get("caminho"):
            try:
                data["texto"] = Path(data["caminho"]).read_text(encoding="utf-8")
            except Exception:
                data["texto"] = ""
        return GeneratedDocumentRecord(**data)


class PostgresExportedFileStore(_BasePostgresStore):
    def list(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_payload FROM exported_files ORDER BY created_at DESC")
                return [self._raw(row["raw_payload"]) for row in cur.fetchall()]

    def create(self, *, file_path: str, file_type: str, source_module: str, source_id: str, title: str = "", metadata: dict[str, Any] | None = None, export_id: str | None = None) -> dict[str, Any]:
        path = Path(file_path)
        created_at = datetime.now(timezone.utc).isoformat()
        payload = {
            "id": export_id or str(uuid4()),
            "arquivo": path.name,
            "caminho": str(path),
            "tipo": file_type,
            "modulo_origem": source_module,
            "id_origem": source_id,
            "titulo": title,
            "tamanho_bytes": path.stat().st_size if path.exists() else 0,
            "criado_em": created_at,
            "metadata": metadata or {},
        }
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO exported_files (id, file_name, file_path, file_type, source_module, source_id, title, size_bytes, raw_payload, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      file_name=EXCLUDED.file_name, file_path=EXCLUDED.file_path, file_type=EXCLUDED.file_type,
                      source_module=EXCLUDED.source_module, source_id=EXCLUDED.source_id, title=EXCLUDED.title,
                      size_bytes=EXCLUDED.size_bytes, raw_payload=EXCLUDED.raw_payload
                    """,
                    (payload["id"], payload["arquivo"], payload["caminho"], payload["tipo"], payload["modulo_origem"],
                     payload["id_origem"], payload["titulo"], payload["tamanho_bytes"], json.dumps(payload, ensure_ascii=False, default=str), payload["criado_em"]),
                )
        return payload
