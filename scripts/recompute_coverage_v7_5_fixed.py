import csv
from pathlib import Path
from datetime import datetime, timezone
import os
import json
# prefer GITHUB_WORKSPACE when running in Actions, fall back to current working dir
ROOT = Path(os.environ.get('GITHUB_WORKSPACE', '.')).resolve()
shadow=ROOT/'shadow_last_cycles.csv'
artifacts=ROOT/'artifacts'
artifacts.mkdir(exist_ok=True)
combos=[]
SYMS=['BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','BNBUSDT']
TFS=['15m','1h','4h']
for s in SYMS:
    for t in TFS:
        combos.append((s,t))

# find last observation per combo
last={c:None for c in combos}
if shadow.exists():
    with open(shadow,'r',encoding='utf-8') as f:
        rows=list(csv.reader(f))
    for row in reversed(rows):
        if len(row)<7: continue
        sym=row[0].strip(); tf=row[1].strip(); note=','.join(row[6:])
        key=(sym,tf)
        if key in last and last[key] is None and 'real_observation' in note:
            ts=row[6].strip()
            if ts.endswith('Z'): ts=ts.replace('Z','+00:00')
            try:
                dt=datetime.fromisoformat(ts)
            except:
                continue
            last[key]=dt

# coverage freshness window per timeframe (minutes)
# Default: strict 120m for 15m/1h, allow 240m for 4h so a recently-closed 4h candle counts
DEFAULT_TF_FRESH_WINDOW = {'15m': 120, '1h': 120, '4h': 240}

# Make the coverage window configurable via environment variables to avoid
# editing this script in the future. Two options are supported (priority order):
#  - COVERAGE_WINDOW_JSON: a JSON string like '{"15m":120,"1h":120,"4h":240}'
#  - COVERAGE_WINDOW_JSON_PATH: path to a JSON file containing the same structure
# If neither provided or parsing fails, the DEFAULT_TF_FRESH_WINDOW is used.
TF_FRESH_WINDOW = DEFAULT_TF_FRESH_WINDOW.copy()
try:
    env_json = os.environ.get('COVERAGE_WINDOW_JSON')
    env_path = os.environ.get('COVERAGE_WINDOW_JSON_PATH')
    if env_json:
        parsed = json.loads(env_json)
        if isinstance(parsed, dict):
            TF_FRESH_WINDOW.update({k: int(v) for k, v in parsed.items()})
    elif env_path:
        p = Path(env_path)
        if p.exists():
            txt = p.read_text(encoding='utf-8')
            parsed = json.loads(txt)
            if isinstance(parsed, dict):
                TF_FRESH_WINDOW.update({k: int(v) for k, v in parsed.items()})
except Exception:
    # fallback silently to defaults if env parsing fails
    TF_FRESH_WINDOW = DEFAULT_TF_FRESH_WINDOW.copy()

# coverage matrix simple: 1 if last within timeframe-specific window
now=datetime.utcnow().replace(tzinfo=timezone.utc)
rows=[]
count2h=0
for (s,t),dt in last.items():
    ok=False
    age=None
    if dt:
        age=(now-dt).total_seconds()/60
        window = TF_FRESH_WINDOW.get(t, 120)
        if age <= window:
            ok=True
    rows.append({'symbol':s,'tf':t,'last_obs':dt.isoformat() if dt else '', 'minutes_ago': round(age,1) if age else '', 'in_2h': 1 if ok else 0})
    if ok: count2h+=1
# write coverage_por_combo
with open(artifacts/'coverage_por_combo_v7_5_fixed.csv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f)
    w.writerow(['symbol','tf','last_obs','minutes_ago','in_2h'])
    for r in rows:
        w.writerow([r['symbol'],r['tf'],r['last_obs'],r['minutes_ago'],r['in_2h']])
# write coverage_matrix_v7.csv minimal form
with open(artifacts/'coverage_matrix_v7.csv','w',encoding='utf-8',newline='') as f:
    w=csv.writer(f)
    w.writerow(['symbol','tf','in_2h'])
    for r in rows:
        w.writerow([r['symbol'],r['tf'],r['in_2h']])
# write an artifact that records the effective coverage window used (for auditability)
try:
    eff = TF_FRESH_WINDOW
    with open(artifacts/'coverage_window_effective.json','w',encoding='utf-8') as f:
        json.dump(eff, f, separators=(',',':'))
except Exception:
    pass
print('wrote', artifacts/'coverage_por_combo_v7_5_fixed.csv','coverage_matrix_v7.csv','coverage_2h_count=',count2h)
