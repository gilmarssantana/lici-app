#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path('/root/lici-app')
BACKUP_ROOT = Path('/root/backups/lici/non-real-data')
MANIFEST_DIR = Path('/root/lici-docs/auditorias')
PATTERN = re.compile(r'\b(AUDIT|AUDITORIA|teste|valida[cç][aã]o|simulad[oa]s?|mock|fake|demo|prot[oó]tipo|exemplo|placeholder)\b', re.I)

FILES = [
    ROOT / 'casos_vivos/casos.json',
    ROOT / 'company_documents/documents.json',
    ROOT / 'company_documents/alerts.json',
    ROOT / 'concorrentes/concorrentes.json',
    ROOT / 'concorrentes/historico.json',
    ROOT / 'consultor_full/leads.json',
    ROOT / 'consultor_full/followups.json',
    ROOT / 'consultor_full/records.json',
    ROOT / 'fornecedor_full/records.json',
    ROOT / 'memoria_viva/memorias.json',
]
INDIVIDUAL_GLOBS = [
    'casos_vivos/*/case.json',
    'memoria_viva/*/*.json',
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text_of(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value)


def is_non_real(record: Any) -> bool:
    return bool(PATTERN.search(text_of(record)))


def already_archived(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    meta = record.get('metadata') if isinstance(record.get('metadata'), dict) else {}
    return record.get('status') == 'arquivado' or meta.get('arquivado') is True


def archive_record(record: dict[str, Any], reason: str) -> bool:
    if already_archived(record):
        metadata = record.setdefault('metadata', {}) if isinstance(record.setdefault('metadata', {}), dict) else {}
        metadata['non_real_data_detected'] = True
        metadata.setdefault('non_real_reason', reason)
        return False
    record['status'] = 'arquivado'
    metadata = record.setdefault('metadata', {})
    if not isinstance(metadata, dict):
        metadata = {}
        record['metadata'] = metadata
    metadata['arquivado'] = True
    metadata['non_real_data_detected'] = True
    metadata['non_real_reason'] = reason
    metadata['arquivado_em'] = now()
    metadata['arquivado_por'] = 'limpeza_produto_real_lici'
    return True


def backup_file(path: Path, backup_dir: Path) -> None:
    if not path.exists():
        return
    dest = backup_dir / path.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)


def process_json_file(path: Path, backup_dir: Path, manifest: list[dict[str, Any]]) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        manifest.append({'arquivo': str(path), 'erro': f'json inválido: {exc}'})
        return 0, 0

    changed = 0
    found = 0

    if isinstance(data, list):
        for index, record in enumerate(data):
            if isinstance(record, dict) and is_non_real(record):
                found += 1
                reason = 'Registro contém marcador de dado não-real/teste/auditoria.'
                did = archive_record(record, reason)
                changed += int(did)
                manifest.append({'arquivo': str(path), 'indice': index, 'id': record.get('id'), 'titulo': record.get('titulo') or record.get('cliente') or record.get('nome') or record.get('objeto'), 'alterado': did})
    elif isinstance(data, dict):
        # common wrappers: {'casos': [...]}, {'itens': [...]}, {'documentos': [...]}
        handled = False
        for key, value in list(data.items()):
            if isinstance(value, list):
                handled = True
                for index, record in enumerate(value):
                    if isinstance(record, dict) and is_non_real(record):
                        found += 1
                        reason = 'Registro contém marcador de dado não-real/teste/auditoria.'
                        did = archive_record(record, reason)
                        changed += int(did)
                        manifest.append({'arquivo': str(path), 'lista': key, 'indice': index, 'id': record.get('id'), 'titulo': record.get('titulo') or record.get('cliente') or record.get('nome') or record.get('objeto'), 'alterado': did})
        if not handled and is_non_real(data):
            found += 1
            reason = 'Registro contém marcador de dado não-real/teste/auditoria.'
            did = archive_record(data, reason)
            changed += int(did)
            manifest.append({'arquivo': str(path), 'id': data.get('id'), 'titulo': data.get('titulo') or data.get('cliente') or data.get('nome') or data.get('objeto'), 'alterado': did})

    if changed:
        backup_file(path, backup_dir)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    return found, changed


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    backup_dir = BACKUP_ROOT / stamp
    manifest: list[dict[str, Any]] = []
    total_found = total_changed = 0

    for path in FILES:
        found, changed = process_json_file(path, backup_dir, manifest)
        total_found += found
        total_changed += changed

    for pattern in INDIVIDUAL_GLOBS:
        for path in ROOT.glob(pattern):
            found, changed = process_json_file(path, backup_dir, manifest)
            total_found += found
            total_changed += changed

    report = {
        'executado_em': now(),
        'backup_dir': str(backup_dir),
        'criterio': PATTERN.pattern,
        'total_detectado': total_found,
        'total_arquivado_ou_alterado': total_changed,
        'observacao': 'Limpeza não destrutiva: registros operacionais artificiais foram arquivados/ocultados, não apagados. Logs históricos não foram removidos.',
        'itens': manifest,
    }
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    out = MANIFEST_DIR / f'LIMPEZA_DADOS_NAO_REAIS_{stamp}.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'manifest': str(out), 'backup_dir': str(backup_dir), 'total_detectado': total_found, 'total_alterado': total_changed}, ensure_ascii=False))


if __name__ == '__main__':
    main()
