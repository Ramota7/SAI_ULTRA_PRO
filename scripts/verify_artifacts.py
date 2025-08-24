#!/usr/bin/env python3
"""
Verifica consistencia de artefactos según `backup_manifest.json`:
- comprueba que el ZIP listado existe y su sha256 coincide
- comprueba que el h5 backup existe y su sha256 coincide
- comprueba exchange_status.json existe y muestra p95 dentro del guardband
- comprueba existencia de attestation y supervisor token y muestra fingerprint
"""
from __future__ import annotations
import json, hashlib, os, sys, subprocess, argparse
from pathlib import Path
import os

# prefer GITHUB_WORKSPACE when running in Actions, fall back to current working dir
ROOT = Path(os.environ.get('GITHUB_WORKSPACE', '.')).resolve()
BM = ROOT / 'backup_manifest.json'


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def read_json(p: Path):
    try:
        return json.load(open(p, 'r', encoding='utf-8'))
    except Exception as e:
        print('ERR reading json', p, e)
        return None


def compute_token_fp(token_path: Path) -> str | None:
    if not token_path.exists():
        return None
    content = token_path.read_text(encoding='utf-8').strip()
    # try to extract an obvious quoted token
    import re
    m = re.search(r"['\"]([A-Za-z0-9_\-]{16,})['\"]", content)
    if m:
        token = m.group(1)
    else:
        token = content
    return hashlib.sha256(token.encode('utf-8')).hexdigest()[:8]


def main(strict_coverage: bool = False):
    if not BM.exists():
        print('MISSING backup_manifest.json')
        return 2
    jm = read_json(BM)
    ok = True
    result = {}

    art = jm.get('artifact_signature', {})
    zipname = art.get('zip')
    if zipname:
        zippath = ROOT / zipname
        if not zippath.exists():
            print('ZIP MISSING:', zippath)
            ok = False
            result['zip_sha_ok'] = False
        else:
            sha = file_sha256(zippath)
            want = art.get('sha256')
            if want != sha:
                print('ZIP sha MISMATCH: manifest=', want, 'actual=', sha)
                ok = False
                result['zip_sha_ok'] = False
            else:
                print('ZIP sha OK:', sha[:16])
                result['zip_sha_ok'] = True
    else:
        print('No artifact_signature.zip in manifest')
        ok = False
        result['zip_sha_ok'] = False

    h5 = jm.get('h5_model_backup', {})
    h5path = ROOT / h5.get('path', '')
    if h5path.exists():
        sha_h5 = file_sha256(h5path)
        want_h5 = h5.get('sha256')
        if sha_h5 != want_h5:
            print('H5 sha MISMATCH: manifest=', want_h5, 'actual=', sha_h5)
            ok = False
            result['backup_restore_ok'] = False
        else:
            print('H5 sha OK:', sha_h5[:16])
            # require restore_dry_run == 'OK' in manifest
            result['backup_restore_ok'] = (h5.get('restore_dry_run') == 'OK')
    else:
        print('H5 MISSING at', h5path)
        ok = False
        result['backup_restore_ok'] = False

    es = ROOT / 'exchange_status.json'
    if es.exists():
        ej = read_json(es)
        p95 = ej.get('p95_ms')
        print('exchange p95_ms =', p95)
        if p95 is not None and abs(p95) > 2000:
            print('WARN: exchange p95 out of guardband')
            ok = False
        result['drift_p95_ms'] = p95
    else:
        print('exchange_status.json missing')
        ok = False
        result['drift_p95_ms'] = None

    # coverage check
    covp = ROOT / 'artifacts' / 'coverage_por_combo_v7_5_fixed.csv'
    coverage_ok = False
    # if strict_coverage requested, run recompute_coverage with strict window
    if strict_coverage:
        try:
            recompute = ROOT / 'scripts' / 'recompute_coverage_v7_5_fixed.py'
            env = os.environ.copy()
            # record the forced window so we can report it later if no marker is written
            forced_window = {'15m':120,'1h':120,'4h':120}
            env['COVERAGE_WINDOW_JSON'] = json.dumps(forced_window)
            print('forcing strict coverage: running recompute_coverage_v7_5_fixed.py')
            proc = subprocess.run([sys.executable, str(recompute)], env=env, capture_output=True, text=True)
            print(proc.stdout)
            if proc.stderr:
                print('recompute stderr:', proc.stderr)
        except Exception as e:
            print('failed to run recompute for strict coverage', e)
    if covp.exists():
        # count in_2h == 1 rows
        with covp.open('r', encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        # skip header
        rows = [l for l in lines[1:]]
        in2h = sum(1 for r in rows if r.split(',')[-1].strip() == '1')
        synthetic = 0  # legacy: shadow_last_cycles has no synthetic marker here
        print('coverage_2h_count=', in2h)
        result['coverage_ok'] = (in2h == 15 and synthetic == 0)
        # indicate if caller forced strict coverage
        result['strict_forced'] = bool(strict_coverage)
        # include metadata about the window used (if recompute script defined it)
        try:
            # Read the recompute script and parse AST to extract TF_FRESH_WINDOW without executing the file
            import ast
            recompute_path = ROOT / 'scripts' / 'recompute_coverage_v7_5_fixed.py'
            txt = recompute_path.read_text(encoding='utf-8')
            tree = ast.parse(txt, filename=str(recompute_path))
            win = None
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id in ('TF_FRESH_WINDOW', 'DEFAULT_TF_FRESH_WINDOW'):
                            try:
                                win = ast.literal_eval(node.value)
                            except Exception:
                                win = None
                            break
                if win is not None:
                    break
            result['coverage_window'] = win or {'15m':120,'1h':120,'4h':240}
            strict = {'15m':120,'1h':120,'4h':120}
            result['coverage_window_override'] = any((result['coverage_window'].get(k, strict[k]) != strict[k]) for k in strict)
        except Exception:
            result['coverage_window'] = {'15m':120,'1h':120,'4h':240}
            result['coverage_window_override'] = False
        # prefer an effective marker written by recompute to reflect exactly what was applied
        try:
            eff_marker = ROOT / 'artifacts' / 'coverage_window_effective.json'
            if eff_marker.exists():
                eff = json.load(open(eff_marker, 'r', encoding='utf-8'))
                result['coverage_window'] = eff
                result['coverage_window_override'] = eff != {'15m':120,'1h':120,'4h':240}
        except Exception:
            pass
    else:
        print('coverage file missing', covp)
        result['coverage_ok'] = False
        result['strict_forced'] = bool(strict_coverage)
        result['coverage_window'] = {'15m':120,'1h':120,'4h':240}
        result['coverage_window_override'] = False

    att = ROOT / 'artifacts' / 'attestation_v7_5.fixed.json'
    if att.exists():
        print('attestation exists ->', att)
    else:
        print('attestation missing ->', att)

    token_path = ROOT / 'sai_ultra_pro' / 'config' / '.supervisor_token.ps1'
    fp = compute_token_fp(token_path)
    if fp:
        print('supervisor token fingerprint (sha256[:8]) ->', fp)
    else:
        print('supervisor token file missing at', token_path)
        ok = False
    result['supervisor_fp'] = fp or None

    # archive/logs
    import glob
    archives = list((ROOT / 'sai_ultra_pro' / 'ia' / 'archive').glob('candidates.*.log.gz'))
    result['archive_count'] = len(archives)
    lr = ROOT / 'sai_ultra_pro' / 'ia' / 'last_rotate.txt'
    if lr.exists():
        result['last_rotate_ts'] = lr.read_text(encoding='utf-8').strip()
    else:
        result['last_rotate_ts'] = None

    # verdict
    result['verdict'] = 'GO' if ok and result.get('coverage_ok') else 'WARN'

    # print compact JSON single-line
    out = json.dumps(result, separators=(',',':'))
    print(out)

    # append audit trace to artifacts/operator.log and artifacts/audit_notes.txt
    try:
        al = ROOT / 'artifacts' / 'operator.log'
        note = ROOT / 'artifacts' / 'audit_notes.txt'
        entry = f"{__file__} verify run result: {out}\n"
        with open(al, 'a', encoding='utf-8') as f:
            f.write(entry)
        with open(note, 'a', encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass

    # return non-zero when the final verdict is not GO so CI/tareas detect WARN
    return 0 if result.get('verdict') == 'GO' else 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict-coverage', dest='strict_coverage', action='store_true', help='Force recompute with strict 4h=120 window before verifying')
    args = parser.parse_args()
    raise SystemExit(main(strict_coverage=args.strict_coverage))
