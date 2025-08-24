#!/usr/bin/env python3
"""Augment existing attestation JSON and ZIP with IP-Gate telemetry and last_ip.txt

Safe: does not alter other attestation fields. If attestation or ZIP missing, it will create minimal attestation JSON
and add telemetry/last_ip to the ZIP if present.
"""
import json, sys, pathlib, zipfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
ART = ROOT / 'artifacts'
ATT = ART / 'attestation_v7_5.fixed.json'
ZIP_NAMES = [
    ROOT / 'AUDITORIA_SOMBRA_MASTER_v7.5.fixed.zip',
    ROOT / 'AUDITORIA_SOMBRA_MASTER_v7.5.zip',
    ROOT / 'AUDITORIA_SOMBRA_MASTER_v7.4.zip',
]
TELE = ROOT / 'sai_ultra_pro' / 'telemetry' / 'ip_gate.json'
LASTIP = ROOT / 'sai_ultra_pro' / 'config' / 'last_ip.txt'

def load_att():
    if ATT.exists():
        try:
            return json.loads(ATT.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}

def save_att(att):
    ATT.parent.mkdir(parents=True, exist_ok=True)
    ATT.write_text(json.dumps(att, ensure_ascii=False, indent=2), encoding='utf-8')

def augment_attestation():
    att = load_att()
    # default fields if missing
    ip_gate = {
        'ip_gate_active': False,
        'ip_detected': None,
        'ip_gate_status': 'UNKNOWN',
        'ip_gate_first_seen_ts': None,
        'ip_gate_last_unblock_ts': None,
        'ip_gate_retries': 0,
        'ip_gate_timeout_s': None,
        'ip_gate_bypass': False,
        'ip_gate_sources': [],
        'allowlist_check_ok': False,
    }
    # merge telemetry if exists
    if TELE.exists():
        try:
            tele = json.loads(TELE.read_text(encoding='utf-8'))
            # map known keys safely
            ip_gate['ip_gate_active'] = bool(tele.get('ip_gate_active', ip_gate['ip_gate_active']))
            ip_gate['ip_detected'] = tele.get('ip_detected', ip_gate['ip_detected'])
            ip_gate['ip_gate_status'] = tele.get('ip_gate_status', ip_gate['ip_gate_status'])
            ip_gate['ip_gate_first_seen_ts'] = tele.get('ip_gate_first_seen_ts', ip_gate['ip_gate_first_seen_ts'])
            ip_gate['ip_gate_retries'] = int(tele.get('ip_gate_retries', ip_gate['ip_gate_retries'] or 0))
            ip_gate['ip_gate_timeout_s'] = int(tele.get('ip_gate_timeout_s', ip_gate['ip_gate_timeout_s'] or 0))
            ip_gate['ip_gate_bypass'] = bool(tele.get('ip_gate_bypass', ip_gate['ip_gate_bypass']))
            ip_gate['ip_gate_sources'] = tele.get('ip_gate_sources', ip_gate['ip_gate_sources']) or []
            ip_gate['allowlist_check_ok'] = bool(tele.get('allowlist_check_ok', ip_gate['allowlist_check_ok']))
            # last_unblock left as None unless telemetry provides
            ip_gate['ip_gate_last_unblock_ts'] = tele.get('ip_gate_last_unblock_ts')
        except Exception:
            pass
    else:
        # try to read last_ip to set ip_detected minimally
        if LASTIP.exists():
            try:
                txt = LASTIP.read_text(encoding='utf-8').strip()
                ip = txt.split('\n',1)[0]
                ip_gate['ip_detected'] = ip
            except Exception:
                pass
    # attach under attestation top-level block 'ip_gate'
    att = att or {}
    att['ip_gate'] = ip_gate
    save_att(att)
    return att


def add_files_to_zip():
    # find first existing ZIP
    for z in ZIP_NAMES:
        if z.exists():
            try:
                with zipfile.ZipFile(str(z), 'a', compression=zipfile.ZIP_DEFLATED) as zf:
                    if TELE.exists():
                        zf.write(str(TELE), arcname='telemetry/ip_gate.json')
                    if LASTIP.exists():
                        zf.write(str(LASTIP), arcname='last_ip.txt')
                return z
            except Exception:
                pass
    return None

if __name__ == '__main__':
    att = augment_attestation()
    z = add_files_to_zip()
    print('ATT updated, ZIP augmented:', z)
    print(json.dumps({'ip_gate': att.get('ip_gate')}))
    sys.exit(0)
