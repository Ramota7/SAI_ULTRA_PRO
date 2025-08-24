"""
Healthcheck ligero para uso local/CI.
- Comprueba sincronización de hora (usa system clock) — compara con time.time() en UTC.
- Reporta CPU/RAM/Disk (psutil si está disponible, fallback a os.statvfs para disco).
- Hace una llamada pública a Binance (ping) para comprobar latencia.
- Envía mensaje de prueba a Telegram si token/chat configurados (no bloqueante).

Ejecutar: python -m sai_ultra_pro.tools.healthcheck
"""
from datetime import datetime, timezone
import time
import os
import json
import socket

def load_config():
    path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def check_ntp_drift():
    # No acceso a NTP server en este entorno, aproximamos comparando UTC time
    local_ts = datetime.now(timezone.utc).timestamp()
    monotonic = time.time()
    # Esto NO es una medida real de NTP drift; placeholder para integrar con ntpdate
    drift_ms = abs((local_ts - monotonic) * 1000)
    return round(drift_ms, 2)


def check_host():
    info = {}
    try:
        import psutil
        info['cpu_percent'] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        info['mem_percent'] = mem.percent
        info['mem_free_mb'] = round(mem.available / 1024 / 1024, 2)
        disk = psutil.disk_usage('.')
        info['disk_percent'] = disk.percent
        info['disk_free_gb'] = round(disk.free / 1024 / 1024 / 1024, 2)
    except Exception:
        # Fallback básico
        info['cpu_percent'] = None
        info['mem_percent'] = None
        info['disk_percent'] = None
    return info


def ping_binance():
    try:
        from sai_ultra_pro.net.http import get as http_get, is_network_allowed
        if not is_network_allowed():
            return {'ok': False, 'error': 'network_disabled_by_env'}
        url = 'https://api.binance.com/api/v3/time'
        t0 = time.time()
        r = http_get(url, timeout=5)
        latency = round((time.time() - t0) * 1000, 2)
        return {'ok': r.status_code == 200, 'latency_ms': latency}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def telegram_test(msg):
    cfg = load_config().get('api_keys', {})
    token = cfg.get('TELEGRAM_BOT_TOKEN')
    chat = cfg.get('TELEGRAM_CHAT_ID')
    if not token or not chat:
        return {'sent': False, 'reason': 'no_token_or_chat'}
    try:
        from sai_ultra_pro.net.http import post as http_post, is_network_allowed
        if not is_network_allowed():
            return {'sent': False, 'reason': 'network_disabled_by_env'}
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        r = http_post(url, data={'chat_id': chat, 'text': msg}, timeout=5)
        return {'sent': r.status_code == 200, 'status_code': r.status_code, 'text': r.text}
    except Exception as e:
        return {'sent': False, 'error': str(e)}


def run_all():
    out = {}
    out['timestamp'] = datetime.now(timezone.utc).astimezone().isoformat()
    out['ntp_drift_ms'] = check_ntp_drift()
    out['host'] = check_host()
    out['binance'] = ping_binance()
    # Non-blocking telegram test: return result but do not raise
    out['telegram_test'] = telegram_test('Healthcheck 24/7 Readiness test')
    return out


if __name__ == '__main__':
    import pprint
    pprint.pprint(run_all())
