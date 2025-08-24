"""Finalize verdict script used by CI.
Loads artifacts from shadow-artifacts and shadow-artifacts-2025, inspects perf.json and verdict.json,
and writes a final artifacts/verdict.json with status 'ok' or 'fail'.
"""
import json
import os
import sys

def load(p):
    try:
        with open(p, 'r', encoding='utf8') as f:
            return json.load(f)
    except Exception:
        return None


def main():
    th = int(os.environ.get('VERDICT_P95_THRESHOLD', '200'))
    unit_result = os.environ.get('UNIT_GATEWAY_RESULT', 'unknown')

    vfiles = ['shadow-artifacts/artifacts/verdict.json', 'shadow-artifacts-2025/artifacts/verdict.json']
    pfiles = ['shadow-artifacts/artifacts/perf.json', 'shadow-artifacts-2025/artifacts/perf.json']

    verdicts = [load(p) for p in vfiles if os.path.exists(p)]
    perfs = [load(p) for p in pfiles if os.path.exists(p)]

    reason = []
    status = 'fail'

    if unit_result != 'success':
        reason.append(f'unit-gateway result: {unit_result}')
    else:
        if any(d and d.get('status') == 'fail' for d in verdicts):
            reason.append('verify-shadow reported fail')
        else:
            p95 = None
            for p in perfs:
                if p and 'p95_ms' in p:
                    try:
                        p95 = int(p['p95_ms'])
                        break
                    except Exception:
                        continue
            if p95 is None:
                reason.append('no perf p95 available')
            elif p95 > th:
                reason.append(f'p95_ms {p95} > threshold {th}')
            else:
                status = 'ok'
                reason.append(f'p95_ms {p95} <= {th}')

    out = {'status': status, 'reason': ' ; '.join(reason), 'p95_ms': (perfs[0].get('p95_ms') if perfs else None)}
    os.makedirs('artifacts', exist_ok=True)
    with open('artifacts/verdict.json', 'w', encoding='utf8') as f:
        json.dump(out, f)
    print(json.dumps(out))


if __name__ == '__main__':
    main()
