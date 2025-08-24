#!/usr/bin/env python3
import sys, os, json, pathlib, zipfile, time
from datetime import datetime

ROOT = pathlib.Path.cwd()
# build search paths
paths = []
art_root = os.environ.get('artifacts_root')
if art_root:
    paths.append(pathlib.Path(art_root))
paths += [ROOT / 'artifacts_ci', ROOT / 'ci_artifacts', ROOT / 'artifacts', ROOT, pathlib.Path(os.path.expanduser('~/Downloads'))]
# dedupe and only existing
seen = set(); search_paths = []
for p in paths:
    try:
        p = p.resolve()
    except Exception:
        p = pathlib.Path(p)
    if str(p) in seen:
        continue
    seen.add(str(p))
    search_paths.append(p)

att_pattern = 'attestation'
zip_pattern = 'AUDITORIA_SOMBRA_MASTER'
att_file = None
zip_file = None
# find most recent attestation*.json
for p in search_paths:
    if not p.exists():
        continue
    files = list(p.rglob('attestation*.json'))
    if files:
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        att_file = files[0]
        break
# find most recent zip
for p in search_paths:
    if not p.exists():
        continue
    files = list(p.rglob('AUDITORIA_SOMBRA_MASTER*.zip'))
    if files:
        files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        zip_file = files[0]
        break

missing = []
ip_ok = False
zip_ipjson = False
zip_last = False
att_obj = None
att_path_str = str(att_file) if att_file else None
zip_path_str = str(zip_file) if zip_file else None
required = ['ip_gate_active','ip_detected','ip_gate_status','ip_gate_first_seen_ts','ip_gate_last_unblock_ts','ip_gate_retries','ip_gate_timeout_s','ip_gate_bypass','ip_gate_sources','allowlist_check_ok']
if not att_file and not zip_file:
    notes = f"NO_ARTIFACTS_FOUND: rutas exploradas={[str(p) for p in search_paths]}"
    verdict = {
        'ok': False,
        'ip_gate_fields_ok': False,
        'missing_fields': ['attestation','zip'],
        'zip_has_ip_gatejson': False,
        'zip_has_last_ip': False,
        'attestation_path': None,
        'zip_path': None,
        'notes': notes
    }
    outp = json.dumps(verdict, ensure_ascii=False)
    outpath = (ROOT / 'artifacts')
    outpath.mkdir(exist_ok=True)
    (outpath / 'CI_VERDICT.json').write_text(outp, encoding='utf-8')
    print(outp)
    sys.exit(0)

if att_file:
    try:
        att_obj = json.loads(att_file.read_text(encoding='utf-8'))
    except Exception as e:
        att_obj = None
        missing = required.copy()

if att_obj and isinstance(att_obj, dict) and 'ip_gate' in att_obj and isinstance(att_obj['ip_gate'], dict):
    ip_block = att_obj['ip_gate']
    for f in required:
        if f not in ip_block:
            missing.append(f)
    ip_ok = (len(missing) == 0)
else:
    missing = required.copy()

if zip_file:
    try:
        with zipfile.ZipFile(zip_file, 'r') as zf:
            entries = zf.namelist()
            zip_ipjson = 'telemetry/ip_gate.json' in entries or 'ip_gate.json' in entries
            zip_last = 'last_ip.txt' in entries
    except Exception:
        zip_ipjson = False
        zip_last = False

ok = ip_ok and zip_ipjson and zip_last
notes_parts = []
if not ip_ok:
    notes_parts.append('missing ip_gate fields')
if not zip_ipjson:
    notes_parts.append('missing telemetry/ip_gate.json in zip')
if not zip_last:
    notes_parts.append('missing last_ip.txt in zip')
notes = '; '.join(notes_parts)
verdict = {
    'ok': ok,
    'ip_gate_fields_ok': ip_ok,
    'missing_fields': missing,
    'zip_has_ip_gatejson': zip_ipjson,
    'zip_has_last_ip': zip_last,
    'attestation_path': att_path_str,
    'zip_path': zip_path_str,
    'notes': notes
}
# write CI_VERDICT.json next to attestation if present else in ./artifacts
out_dir = att_file.parent if att_file else (ROOT / 'artifacts')
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / 'CI_VERDICT.json').write_text(json.dumps(verdict, ensure_ascii=False), encoding='utf-8')
print(json.dumps(verdict, ensure_ascii=False))
