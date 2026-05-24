from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.schemas.document_generator import GeneratedDocumentRecord
from app.schemas.upload import UploadDocumentRecord
from app.services.document_pg_store import PostgresExportedFileStore, PostgresGeneratedDocumentStore, PostgresUploadDocumentStore


def create_schema() -> None:
    store = PostgresUploadDocumentStore()
    if not store.dsn:
        raise RuntimeError("LICI_DATABASE_URL não configurado")
    import psycopg
    with psycopg.connect(store.dsn, connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS uploaded_documents (
                  id text PRIMARY KEY,
                  original_name text NOT NULL,
                  stored_name text,
                  file_path text NOT NULL,
                  content_type text,
                  extension text,
                  size_bytes bigint,
                  status text,
                  extracted_chars integer,
                  case_id text,
                  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz,
                  updated_at timestamptz
                );
                CREATE INDEX IF NOT EXISTS idx_uploaded_documents_status ON uploaded_documents (status);
                CREATE INDEX IF NOT EXISTS idx_uploaded_documents_case_id ON uploaded_documents (case_id);
                CREATE INDEX IF NOT EXISTS idx_uploaded_documents_extension ON uploaded_documents (extension);

                CREATE TABLE IF NOT EXISTS generated_documents (
                  id text PRIMARY KEY,
                  document_type text,
                  title text,
                  file_name text,
                  file_path text NOT NULL,
                  client_name text,
                  orgao_name text,
                  process text,
                  modality text,
                  object text,
                  case_id text,
                  uploaded_document_id text,
                  base_decision text,
                  base_score integer,
                  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz
                );
                CREATE INDEX IF NOT EXISTS idx_generated_documents_type ON generated_documents (document_type);
                CREATE INDEX IF NOT EXISTS idx_generated_documents_case_id ON generated_documents (case_id);
                CREATE INDEX IF NOT EXISTS idx_generated_documents_uploaded_id ON generated_documents (uploaded_document_id);

                CREATE TABLE IF NOT EXISTS exported_files (
                  id text PRIMARY KEY,
                  file_name text NOT NULL,
                  file_path text NOT NULL,
                  file_type text,
                  source_module text,
                  source_id text,
                  title text,
                  size_bytes bigint,
                  raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
                  created_at timestamptz
                );
                CREATE INDEX IF NOT EXISTS idx_exported_files_type ON exported_files (file_type);
                CREATE INDEX IF NOT EXISTS idx_exported_files_source ON exported_files (source_module, source_id);
                CREATE INDEX IF NOT EXISTS idx_exported_files_created ON exported_files (created_at);
                """
            )


def _load(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def migrate() -> dict[str, int]:
    create_schema()
    upload_store = PostgresUploadDocumentStore()
    generated_store = PostgresGeneratedDocumentStore()
    export_store = PostgresExportedFileStore()
    counts = {"uploaded_documents": 0, "generated_documents": 0, "exported_files": 0}

    for raw in _load("/root/lici-app/storage/documentos.json"):
        upload_store.upsert(UploadDocumentRecord(**raw))
        counts["uploaded_documents"] += 1

    for raw in _load("/root/lici-app/storage/documentos_gerados/index.json"):
        generated_store.upsert(GeneratedDocumentRecord(**raw))
        counts["generated_documents"] += 1

    export_dir = Path("/root/lici-app/storage/exportados")
    if export_dir.exists():
        for path in sorted(p for p in export_dir.rglob("*") if p.is_file()):
            export_store.create(
                file_path=str(path),
                file_type=path.suffix.lstrip(".").lower(),
                source_module="filesystem_migration",
                source_id=path.stem,
                title=path.name,
                metadata={"migrado_de_filesystem": True},
                export_id=f"fs-{path.name}-{int(path.stat().st_mtime)}",
            )
            counts["exported_files"] += 1
    return counts


if __name__ == "__main__":
    print(json.dumps(migrate(), ensure_ascii=False, indent=2))
