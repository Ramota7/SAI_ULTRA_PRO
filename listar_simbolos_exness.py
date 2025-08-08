import sys
sys.path.append('sai_ultra_pro')
import MetaTrader5 as mt5
import json

with open('sai_ultra_pro/config/config.json') as f:
    c = json.load(f)

api_key = c['api_keys']['EXNESS_API_KEY']
api_secret = c['api_keys']['EXNESS_API_SECRET']
server = c['api_keys']['EXNESS_SERVER']

if not mt5.initialize(server=server, login=int(api_key), password=api_secret):
    print(f"[ERROR] No se pudo conectar a Exness: {mt5.last_error()}")
    sys.exit(1)

symbols = mt5.symbols_get()
print(f"Total símbolos disponibles: {len(symbols)}")
for s in symbols:
    print(f"{s.name} | Visible: {s.visible} | Path: {s.path}")

mt5.shutdown()
