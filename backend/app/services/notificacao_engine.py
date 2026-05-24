from __future__ import annotations

import hashlib
import json
import os
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import HTTPException, status

from app.schemas.notificacao import NotificationLogRecord, NotificationResponse, NotificationSendRequest, NotificationTestRequest
from app.services.audit_log import audit_event
from app.services.observability import structured_log

ROOT = Path('/root/lici-app/notificacoes')
CONFIG_PATH = ROOT / 'config.json'
LOGS_PATH = ROOT / 'logs.json'

DEFAULT_CONFIG = {
    'enabled': False,
    'provider': 'telegram',
    'cooldown_minutes': 30,
    'max_per_hour': 10,
    'telegram': {
        'enabled': False,
        'bot_token_env': 'LICI_TELEGRAM_BOT_TOKEN',
        'bot_token': '',
        'chat_id': '',
        'parse_mode': 'HTML',
    },
    'eventos_notificaveis': [
        'oportunidade_prioridade_alta',
        'alerta_critico',
        'risco_concorrencial_alto',
        'falha_backup',
        'healthcheck_erro',
        'prazo_critico',
        'teste',
    ],
}


class LiciNotificationEngine:
    def __init__(self):
        ROOT.mkdir(parents=True, exist_ok=True)
        if not CONFIG_PATH.exists():
            self._write_json(CONFIG_PATH, DEFAULT_CONFIG)
            try:
                CONFIG_PATH.chmod(0o600)
            except Exception:
                pass
        if not LOGS_PATH.exists():
            self._write_json(LOGS_PATH, [])

    def info(self) -> dict[str, Any]:
        cfg = self._config()
        logs = self._logs()
        return {
            'nome': 'LICI Notificações Externas Engine',
            'status': 'ativo' if cfg.get('enabled') else 'desabilitado',
            'provider': cfg.get('provider', 'telegram'),
            'enabled': bool(cfg.get('enabled')),
            'canais': {'telegram': self._telegram_ready(cfg)},
            'config_path': str(CONFIG_PATH),
            'logs_path': str(LOGS_PATH),
            'eventos_notificaveis': cfg.get('eventos_notificaveis', []),
            'antispam': {'cooldown_minutes': cfg.get('cooldown_minutes', 30), 'max_per_hour': cfg.get('max_per_hour', 10)},
            'metricas': self.metrics(),
            'regras': ['JWT obrigatório', 'admin obrigatório', 'sem WhatsApp na Fase 1', 'habilitar/desabilitar via config.json', 'anti-spam por cooldown e limite/hora'],
        }

    def testar(self, payload: NotificationTestRequest, user: dict[str, Any]) -> NotificationResponse:
        req = NotificationSendRequest(
            tipo='teste',
            titulo='Teste de Notificação LICI',
            mensagem='Mensagem de teste da LICI Notificações Externas — Fase 1.',
            canal=payload.canal,
            dry_run=payload.dry_run,
            forcar=True,
            metadata={'teste': True},
        )
        return self.enviar(req, user)

    def enviar(self, payload: NotificationSendRequest, user: dict[str, Any]) -> NotificationResponse:
        cfg = self._config()
        canal = payload.canal or cfg.get('provider', 'telegram')
        dedupe_key = self._dedupe_key(payload, canal)
        destino = self._destination(cfg, canal)

        if payload.tipo not in set(cfg.get('eventos_notificaveis', [])):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='tipo de evento não notificável')

        if not payload.forcar:
            blocked = self._blocked_by_antispam(cfg, dedupe_key)
            if blocked:
                log = self._append_log(payload, canal, 'bloqueado_antispam', destino, dedupe_key, payload.dry_run, blocked)
                audit_event('notificacoes', 'envio_bloqueado_antispam', 'alerta', {'tipo': payload.tipo, 'motivo': blocked, 'usuario': user.get('usuario')}, log.id)
                structured_log('api', 'notification_blocked_antispam', 'alerta', {'tipo': payload.tipo, 'motivo': blocked})
                return NotificationResponse(status='bloqueado_antispam', enviado=False, canal=canal, destino=destino, motivo=blocked, log=log)

        if payload.dry_run:
            log = self._append_log(payload, canal, 'dry_run', destino, dedupe_key, True, '')
            audit_event('notificacoes', 'teste_notificacao' if payload.tipo == 'teste' else 'notificacao_dry_run', 'ok', {'tipo': payload.tipo, 'canal': canal, 'usuario': user.get('usuario')}, log.id)
            structured_log('api', 'notification_dry_run', 'ok', {'tipo': payload.tipo, 'canal': canal})
            return NotificationResponse(status='dry_run', enviado=False, canal=canal, destino=destino, motivo='dry_run: nenhuma mensagem externa enviada', log=log)

        if not cfg.get('enabled'):
            log = self._append_log(payload, canal, 'desabilitado', destino, dedupe_key, False, 'notificações desabilitadas')
            audit_event('notificacoes', 'envio_ignorado_desabilitado', 'alerta', {'tipo': payload.tipo, 'canal': canal, 'usuario': user.get('usuario')}, log.id)
            structured_log('api', 'notification_disabled', 'alerta', {'tipo': payload.tipo, 'canal': canal})
            return NotificationResponse(status='desabilitado', enviado=False, canal=canal, destino=destino, motivo='notificações desabilitadas em config.json', log=log)

        try:
            if canal != 'telegram':
                raise ValueError('Fase 1 suporta apenas telegram')
            self._send_telegram(cfg, payload)
            log = self._append_log(payload, canal, 'enviado', destino, dedupe_key, False, '')
            audit_event('notificacoes', 'notificacao_enviada', 'ok', {'tipo': payload.tipo, 'canal': canal, 'destino': self._mask(destino), 'usuario': user.get('usuario')}, log.id)
            structured_log('api', 'notification_sent', 'ok', {'tipo': payload.tipo, 'canal': canal})
            return NotificationResponse(status='enviado', enviado=True, canal=canal, destino=destino, log=log)
        except Exception as exc:
            log = self._append_log(payload, canal, 'erro', destino, dedupe_key, False, str(exc))
            audit_event('notificacoes', 'falha_envio_notificacao', 'erro', {'tipo': payload.tipo, 'canal': canal, 'erro': str(exc), 'usuario': user.get('usuario')}, log.id)
            structured_log('api', 'notification_send_failed', 'erro', {'tipo': payload.tipo, 'canal': canal, 'erro': str(exc)})
            return NotificationResponse(status='erro', enviado=False, canal=canal, destino=destino, motivo=str(exc), log=log)

    def logs(self) -> dict[str, Any]:
        logs = list(reversed(self._logs()))
        return {'total': len(logs), 'logs': logs}

    def get_log(self, log_id: str) -> dict[str, Any]:
        for log in self._logs():
            if log.get('id') == log_id:
                return log
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='log de notificação não encontrado')

    def arquivar_log(self, log_id: str, user: dict[str, Any]) -> dict[str, Any]:
        logs = self._logs(); found = None
        for log in logs:
            if log.get('id') == log_id:
                log.setdefault('metadata', {})['arquivado'] = True
                log['metadata']['arquivado_em'] = datetime.now(timezone.utc).isoformat()
                found = log
                break
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='log de notificação não encontrado')
        self._write_json(LOGS_PATH, logs)
        audit_event('notificacoes', 'arquivamento_log_notificacao', 'ok', {'status': found.get('status'), 'usuario': user.get('usuario')}, log_id)
        return found

    def metrics(self) -> dict[str, Any]:
        logs = self._logs()
        last_24 = [log for log in logs if self._within_hours(log.get('timestamp'), 24)]
        return {
            'total_logs': len(logs),
            'ultimas_24h': len(last_24),
            'enviadas_24h': sum(1 for log in last_24 if log.get('status') == 'enviado'),
            'erros_24h': sum(1 for log in last_24 if log.get('status') == 'erro'),
            'bloqueadas_antispam_24h': sum(1 for log in last_24 if log.get('status') == 'bloqueado_antispam'),
            'ultimo_status': logs[-1].get('status') if logs else None,
            'ultimo_evento': logs[-1].get('tipo') if logs else None,
        }

    def _send_telegram(self, cfg: dict[str, Any], payload: NotificationSendRequest) -> None:
        tg = cfg.get('telegram') or {}
        if not tg.get('enabled'):
            raise ValueError('telegram desabilitado em config.json')
        token = tg.get('bot_token') or os.getenv(tg.get('bot_token_env') or 'LICI_TELEGRAM_BOT_TOKEN')
        chat_id = tg.get('chat_id')
        if not token or not chat_id:
            raise ValueError('telegram sem bot_token/chat_id configurado')
        text = self._format_message(payload)
        data = urllib.parse.urlencode({'chat_id': chat_id, 'text': text, 'parse_mode': tg.get('parse_mode') or 'HTML', 'disable_web_page_preview': 'true'}).encode('utf-8')
        req = urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage', data=data, method='POST')
        with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as response:
            raw = response.read().decode('utf-8')
            result = json.loads(raw)
            if not result.get('ok'):
                raise RuntimeError(raw)

    def _format_message(self, payload: NotificationSendRequest) -> str:
        ref = f"\n<b>Referência:</b> {self._escape(payload.referencia_id)}" if payload.referencia_id else ''
        return f"⚖️ <b>LICI — {self._escape(payload.titulo)}</b>\n<b>Tipo:</b> {self._escape(payload.tipo)}\n<b>Severidade:</b> {self._escape(payload.severidade)}{ref}\n\n{self._escape(payload.mensagem)}"

    def _blocked_by_antispam(self, cfg: dict[str, Any], dedupe_key: str) -> str:
        logs = self._logs()
        cooldown = int(cfg.get('cooldown_minutes') or 30)
        max_hour = int(cfg.get('max_per_hour') or 10)
        recent_hour = [log for log in logs if self._within_hours(log.get('timestamp'), 1) and log.get('status') in {'enviado', 'dry_run'}]
        if len(recent_hour) >= max_hour:
            return f'limite horário atingido ({max_hour}/h)'
        for log in reversed(logs):
            if log.get('dedupe_key') != dedupe_key or log.get('status') not in {'enviado', 'dry_run', 'desabilitado'}:
                continue
            ts = self._parse_dt(log.get('timestamp'))
            if ts and datetime.now(timezone.utc) - ts < timedelta(minutes=cooldown):
                return f'cooldown ativo para evento semelhante ({cooldown} min)'
            break
        return ''

    def _append_log(self, payload: NotificationSendRequest, canal: str, status_value: str, destino: str, dedupe_key: str, dry_run: bool, erro: str) -> NotificationLogRecord:
        record = NotificationLogRecord(tipo=payload.tipo, titulo=payload.titulo, canal=canal, status=status_value, destino=self._mask(destino), referencia_id=payload.referencia_id, dedupe_key=dedupe_key, dry_run=dry_run, erro=erro, metadata=payload.metadata)
        logs = self._logs()
        logs.append(record.model_dump())
        logs = logs[-1000:]
        self._write_json(LOGS_PATH, logs)
        return record

    def _config(self) -> dict[str, Any]:
        try:
            current = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        except Exception:
            current = {}
        merged = {**DEFAULT_CONFIG, **current}
        merged['telegram'] = {**DEFAULT_CONFIG['telegram'], **(current.get('telegram') or {})}
        return merged

    def _logs(self) -> list[dict[str, Any]]:
        try:
            raw = json.loads(LOGS_PATH.read_text(encoding='utf-8'))
            return raw if isinstance(raw, list) else []
        except Exception:
            return []

    def _write_json(self, path: Path, data: Any) -> None:
        with NamedTemporaryFile('w', encoding='utf-8', dir=ROOT, delete=False) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2, default=str)
            tmp.write('\n')
            tmp_path = Path(tmp.name)
        tmp_path.replace(path)

    def _dedupe_key(self, payload: NotificationSendRequest, canal: str) -> str:
        raw = '|'.join([canal, payload.tipo, payload.referencia_id or '', payload.titulo.strip().casefold()])
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]

    def _destination(self, cfg: dict[str, Any], canal: str) -> str:
        if canal == 'telegram':
            return str((cfg.get('telegram') or {}).get('chat_id') or '')
        return ''

    def _telegram_ready(self, cfg: dict[str, Any]) -> dict[str, Any]:
        tg = cfg.get('telegram') or {}
        token = tg.get('bot_token') or os.getenv(tg.get('bot_token_env') or 'LICI_TELEGRAM_BOT_TOKEN')
        return {'enabled': bool(tg.get('enabled')), 'chat_id_configurado': bool(tg.get('chat_id')), 'token_configurado': bool(token)}

    def _mask(self, value: str) -> str:
        if not value:
            return ''
        value = str(value)
        if len(value) <= 6:
            return '***'
        return f'{value[:3]}***{value[-3:]}'

    def _within_hours(self, value: str | None, hours: int) -> bool:
        ts = self._parse_dt(value)
        return bool(ts and datetime.now(timezone.utc) - ts <= timedelta(hours=hours))

    def _parse_dt(self, value: str | None):
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None

    def _escape(self, value: Any) -> str:
        text = str(value or '')
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
