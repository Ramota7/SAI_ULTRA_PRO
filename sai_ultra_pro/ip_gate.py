import time
import json
import pathlib
import threading
import os
from sai_ultra_pro.net.http import get as http_get, is_network_allowed
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
LAST_IP_FILE = CONFIG_DIR / "last_ip.txt"
IP_CMD_FILE = CONFIG_DIR / "ip_gate_cmd"
TELEMETRY_FILE = ROOT / "telemetry" / "ip_gate.json"
TELEMETRY_FILE.parent.mkdir(parents=True, exist_ok=True)

# Defaults (env overrides)
RETRY = int(float(os.environ.get('IP_GATE_RETRY', 30)))
MAX_WAIT = int(float(os.environ.get('IP_GATE_MAX_WAIT', 15 * 60)))
ALERT_EVERY = int(float(os.environ.get('IP_GATE_ALERT_EVERY', 5 * 60)))
SKIP = os.environ.get('SKIP_IP_GATE', '0') == '1'


def _now_ts():
    return datetime.now(timezone.utc).isoformat()


def _detect_ip():
    services = [
        ('https://api.ipify.org', {}),
        ('https://ifconfig.co/ip', {'headers': {'Accept': 'text/plain'}}),
    ]
    ips = []
    for url, opts in services:
        try:
            # Usar wrapper HTTP que respeta TEST_NO_NETWORK
            r = http_get(url, timeout=5, **opts)
            if r.status_code == 200:
                ip = r.text.strip()
                ips.append(ip)
        except Exception:
            ips.append(None)
    # prefer first non-None that matches others or return first
    non_null = [i for i in ips if i]
    return non_null[0] if non_null else None


def _read_last_ip():
    try:
        text = LAST_IP_FILE.read_text(encoding='utf-8').strip()
        ip, ts = text.split('\n')
        return ip, ts
    except Exception:
        return None, None


def _write_last_ip(ip):
    LAST_IP_FILE.write_text(f"{ip}\n{_now_ts()}", encoding='utf-8')


def _write_telemetry(data):
    try:
        TELEMETRY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def _notify(msg, telegram_send=None):
    # log
    print(f"[IP_GATE] {msg}")
    # telegram if provided
    try:
        if telegram_send:
            telegram_send(msg)
    except Exception:
        pass


class IPGate:
    def __init__(self, telegram_send=None):
        self.telegram_send = telegram_send
        self.status = 'OK'
        self.detected_ip = None
        self.first_seen = None
        self.retries = 0

    def preflight(self):
        if SKIP:
            print('[IP_GATE] SKIP_IP_GATE=1 set, bypassing gate')
            return True

        ip, ts = _read_last_ip()
        current = _detect_ip()
        self.detected_ip = current
        self.first_seen = _now_ts()
        telemetry = {
            'ip_gate_active': True,
            'ip_detected': current,
            'ip_gate_status': 'OK',
            'ip_gate_first_seen_ts': self.first_seen,
            'ip_gate_retries': 0,
        }
        _write_telemetry(telemetry)

        if not current:
            _notify('No pude detectar IP pública desde servicios', self.telegram_send)
            self.status = 'BLOCKED'
            telemetry['ip_gate_status'] = 'BLOCKED'
            _write_telemetry(telemetry)
            return False

        if ip == current:
            # same as last known
            _write_last_ip(current)
            telemetry['ip_gate_status'] = 'OK'
            _write_telemetry(telemetry)
            return True

        # IP differs -> enter BLOCKED_IP
        self.status = 'BLOCKED'
        start = time.time()
        last_alert = 0
        _notify(f"IP detectada: {current}. Actualiza la allowlist/credenciales y responde IP_OK para continuar.", self.telegram_send)

        while time.time() - start < MAX_WAIT:
            self.retries += 1
            telemetry['ip_gate_retries'] = self.retries
            telemetry['ip_detected'] = current
            telemetry['ip_gate_status'] = 'BLOCKED'
            _write_telemetry(telemetry)

            # check local confirmation file
            try:
                if IP_CMD_FILE.exists():
                    cmd = IP_CMD_FILE.read_text(encoding='utf-8').strip()
                    if cmd == 'IP_OK':
                        _notify('Control local IP_OK recibido; reanudando.', self.telegram_send)
                        self.status = 'OK'
                        _write_last_ip(current)
                        telemetry['ip_gate_status'] = 'OK'
                        _write_telemetry(telemetry)
                        try:
                            IP_CMD_FILE.unlink()
                        except Exception:
                            pass
                        return True
            except Exception:
                pass

            # test signed API (best effort) - here we perform a dummy HTTP check if credentials exist in config
            # We try to read a credentials file but never print secrets.
            try:
                conf_file = CONFIG_DIR / 'credentials.json'
                if conf_file.exists():
                    conf = json.loads(conf_file.read_text(encoding='utf-8'))
                    # placeholder for ping endpoint, use any configured api endpoint conservatively
                    api_base = conf.get('api_base')
                    token = conf.get('token')
                    if api_base and token:
                        try:
                            # attempt a minimal authenticated GET; redact token from logs
                            h = {'Authorization': f"Bearer {token[:8]}..."}
                            # usar wrapper
                            r = http_get(api_base, headers=h, timeout=5)
                            if r.status_code == 200:
                                _notify('Ping autenticado exitoso; IP aceptada.', self.telegram_send)
                                self.status = 'OK'
                                _write_last_ip(current)
                                telemetry['ip_gate_status'] = 'OK'
                                _write_telemetry(telemetry)
                                return True
                        except Exception:
                            pass
            except Exception:
                pass

            # periodic alert
            if time.time() - last_alert > ALERT_EVERY:
                _notify(f"IP detectada: {current}. Actualiza la allowlist/credenciales y responde IP_OK para continuar.", self.telegram_send)
                last_alert = time.time()

            time.sleep(RETRY)

        # timeout
        self.status = 'TIMEOUT'
        telemetry['ip_gate_status'] = 'TIMEOUT'
        _write_telemetry(telemetry)
        _notify('IP_GATE_TIMEOUT', self.telegram_send)
        return False


# Convenience function
def run_preflight_and_block_if_needed(telegram_send=None):
    gate = IPGate(telegram_send=telegram_send)
    ok = gate.preflight()
    return ok
