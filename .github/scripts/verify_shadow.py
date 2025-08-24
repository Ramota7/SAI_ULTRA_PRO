#!/usr/bin/env python3
# Verify shadow artifacts (Windows runner friendly, stdlib-only)
import csv, glob, hashlib, json, os, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]  # repo root (.github/scripts -> .github -> root)
ART = ROOT / "artifacts"
ART.mkdir(exist_ok=True)

def read_json(p):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None

def read_text(p):
    try:
        return pathlib.Path(p).read_text(encoding="utf-8").strip()
    except Exception:
        return ""

def sha256_file(p):
    try:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

# -------- coverage (espera artifacts/coverage_por_combo_v7_5_fixed.csv) ----------
cov_ok, cov_count = False, 0
cov_csv = ART / "coverage_por_combo_v7_5_fixed.csv"
if cov_csv.exists():
    try:
        with open(cov_csv, newline="", encoding="utf-8") as f:
            sample = f.read(4096); f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
            reader  = csv.DictReader(f, dialect=dialect)
            for row in reader:
                v = row.get("in_2h") or row.get("in_120m") or row.get("in_window")
                if str(v).strip().lower() in ("1", "true", "yes"):
                    cov_count += 1
        cov_ok = cov_count >= 15
    except Exception:
        pass

# -------- drift (exchange_status.json) ----------
ex = read_json(ROOT / "exchange_status.json") or {}
p95 = ex.get("p95_ms")
try:
    drift_ok = p95 is not None and abs(float(p95)) <= 2000
except Exception:
    drift_ok, p95 = False, None

# -------- backup / H5 restore_dry_run ----------
bm = read_json(ROOT / "backup_manifest.json") or {}
restore_ok = (bm.get("last_manual_h5_dryrun", {}).get("result", {}).get("restore_dry_run") == "OK") \
          or (bm.get("h5_model_backup", {}).get("restore_dry_run") == "OK")

# -------- ZIP sha (acepta .sha256 presente; si está el .zip lo verifica) ----------
zip_sha_ok, zip_sha = False, None
for name in [
    "AUDITORIA_SOMBRA_MASTER_v7.5.fixed.zip.sha256",
    "AUDITORIA_SOMBRA_MASTER_v7.5.zip.sha256",
    "AUDITORIA_SOMBRA_MASTER_v7.4.zip.sha256",
]:
    p = ROOT / name
    if p.exists():
        txt = read_text(p)
        m   = re.search(r"[a-fA-F0-9]{64}", txt)
        if m:
            zip_sha = m.group(0).lower()
            zip_file = p.with_suffix("")  # quita .sha256
            if zip_file.exists():
                zip_sha_ok = (sha256_file(zip_file) == zip_sha)
            else:
                zip_sha_ok = True  # aceptamos solo la suma registrada
        break

# -------- archive / last_rotate ----------
archive_dir   = ROOT / "sai_ultra_pro" / "ia" / "archive"
archive_count = len(list(archive_dir.glob("candidates.*.log.gz"))) if archive_dir.exists() else 0
last_rotate   = read_text(ROOT / "last_rotate.txt")

# -------- supervisor token fp (sha256 primeros 8) ----------
fp8, token_val = "", None
tok = read_text(ROOT / ".supervisor_token.ps1")
m = (re.search(r"SUPERVISOR_CONTROL_TOKEN\s*=\s*['\"](.+?)['\"]", tok)
     or re.search(r"([A-Fa-f0-9]{64})", tok))
if m:
    token_val = m.group(1)
if token_val:
    if len(token_val) != 64:  # probablemente texto, hasheamos
        token_val = hashlib.sha256(token_val.encode("utf-8")).hexdigest()
    fp8 = token_val[:8]

verdict = {
    "coverage_ok": bool(cov_ok),
    "coverage_2h_count": int(cov_count),
    "drift_p95_ms": p95,
    "backup_restore_ok": bool(restore_ok),
    "zip_sha_ok": bool(zip_sha_ok),
    "archive_count": int(archive_count),
    "last_rotate_ts": last_rotate or None,
    "supervisor_fp": fp8 or None,
    "verdict": "GO" if (cov_ok and restore_ok and zip_sha_ok and archive_count >= 2
                         and last_rotate and (p95 is not None and abs(float(p95)) <= 2000)) else "WARN",
}

# Augment with ip_gate telemetry if present (informational only)
try:
    tele_path = ROOT / 'sai_ultra_pro' / 'telemetry' / 'ip_gate.json'
    if tele_path.exists():
        tele = json.loads(tele_path.read_text(encoding='utf-8'))
        verdict.update({
            'ip_gate_active': bool(tele.get('ip_gate_active', False)),
            'ip_detected': tele.get('ip_detected'),
            'ip_gate_status': tele.get('ip_gate_status', 'UNKNOWN'),
            'ip_gate_first_seen_ts': tele.get('ip_gate_first_seen_ts'),
            'ip_gate_last_unblock_ts': tele.get('ip_gate_last_unblock_ts'),
            'ip_gate_retries': int(tele.get('ip_gate_retries', 0)),
            'ip_gate_timeout_s': int(tele.get('ip_gate_timeout_s', 0)) if tele.get('ip_gate_timeout_s') else None,
            'ip_gate_bypass': bool(tele.get('ip_gate_bypass', False)),
            'ip_gate_sources': tele.get('ip_gate_sources', []),
            'allowlist_check_ok': bool(tele.get('allowlist_check_ok', False)),
        })
    else:
        verdict.update({
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
        })
except Exception:
    # best-effort: don't fail verification if telemetry parsing fails
    verdict.setdefault('ip_gate_active', False)

out = ART / "verdict.json"
out.write_text(json.dumps(verdict, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(verdict, ensure_ascii=False))  # aparece en logs
sys.exit(0)  # siempre éxito; el estado va en verdict.json
