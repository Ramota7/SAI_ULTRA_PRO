#!/usr/bin/env python3
"""Mini CI: ejecuta recompute y verify (normal + strict) y comprueba veredictos.

Uso: python scripts/ci_verify_strict.py [--expect-normal GO|WARN] [--expect-strict GO|WARN]
"""
from __future__ import annotations
import subprocess, sys, json, argparse
from pathlib import Path

ROOT = Path(r"C:\Proyectos\SAI_ULTRA_PRO II")

def run_cmd(args, env=None):
    p = subprocess.run(args, capture_output=True, text=True, env=env)
    out = p.stdout.strip() + ("\n"+p.stderr.strip() if p.stderr.strip() else "")
    return p.returncode, out

def extract_json_line(text):
    # get last line that looks like JSON (starts with '{' and ends with '}')
    for line in reversed(text.splitlines()):
        s = line.strip()
        if s.startswith('{') and s.endswith('}'):
            try:
                return json.loads(s)
            except Exception:
                continue
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expect-normal', default='GO')
    parser.add_argument('--expect-strict', default='WARN')
    args = parser.parse_args()

    recompute = [sys.executable, str(ROOT / 'scripts' / 'recompute_coverage_v7_5_fixed.py')]
    verify = [sys.executable, str(ROOT / 'scripts' / 'verify_artifacts.py')]

    print('1) Ejecutando recompute (normal)')
    rc, out = run_cmd(recompute)
    print(out)
    if rc != 0:
        print('recompute falló', rc)
        raise SystemExit(2)

    print('\n2) Ejecutando verify (normal)')
    rc, out = run_cmd(verify)
    print(out)
    if rc != 0:
        print('verify normal devolvió código', rc)
    j = extract_json_line(out)
    if not j:
        print('No se pudo parsear JSON de verify normal')
        raise SystemExit(3)
    normal_verdict = j.get('verdict')

    print('\n3) Ejecutando verify (strict)')
    rc, out = run_cmd(verify + ['--strict-coverage'])
    print(out)
    if rc != 0:
        print('verify strict devolvió código', rc)
    j2 = extract_json_line(out)
    if not j2:
        print('No se pudo parsear JSON de verify strict')
        raise SystemExit(4)
    strict_verdict = j2.get('verdict')

    ok = True
    if normal_verdict != args.expect_normal:
        print(f"ERROR: expected normal {args.expect_normal} but got {normal_verdict}")
        ok = False
    else:
        print('Normal verdict as expected:', normal_verdict)

    if strict_verdict != args.expect_strict:
        print(f"ERROR: expected strict {args.expect_strict} but got {strict_verdict}")
        ok = False
    else:
        print('Strict verdict as expected:', strict_verdict)

    raise SystemExit(0 if ok else 5)

if __name__ == '__main__':
    main()
