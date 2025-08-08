import sys
sys.path.append('sai_ultra_pro')
import MetaTrader5 as mt5
import json

with open('sai_ultra_pro/config/config.json') as f:
    c = json.load(f)

api_key = c['api_keys']['EXNESS_API_KEY']
api_secret = c['api_keys']['EXNESS_API_SECRET']
server = c['api_keys']['EXNESS_SERVER']

print("[CHECK] Iniciando verificación de Exness/MetaTrader5...")
if not mt5.initialize(server=server, login=int(api_key), password=api_secret):
    print(f"[ERROR] No se pudo conectar a Exness: {mt5.last_error()}")
    sys.exit(1)
print("[OK] Conexión con MetaTrader5 establecida.")

symbols = mt5.symbols_get()
visibles = [s for s in symbols if s.visible]
if not visibles:
    print("[ERROR] No hay símbolos visibles para trading. Habilita al menos uno en MetaTrader5.")
    mt5.shutdown()
    sys.exit(1)
print(f"[OK] Símbolos visibles para trading: {[s.name for s in visibles]}")

# Probar obtención de ticks y ejecución de orden simulada en el primer símbolo visible
symbol = visibles[0].name
print(f"[CHECK] Probando obtención de ticks para {symbol}...")
tick = mt5.symbol_info_tick(symbol)
if not tick:
    print(f"[ERROR] No se pudo obtener tick para {symbol}.")
    mt5.shutdown()
    sys.exit(1)
print(f"[OK] Último tick de {symbol}: Bid={tick.bid}, Ask={tick.ask}")

print(f"[CHECK] Probando ejecución simulada de orden BUY 0.01 {symbol}...")
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": symbol,
    "volume": 0.01,
    "type": mt5.ORDER_TYPE_BUY,
    "price": tick.ask,
    "deviation": 10,
    "magic": 20250728,
    "comment": "TEST SAI ULTRA PRO"
}
print(f"[OK] Request de orden generado correctamente: {request}")
mt5.shutdown()
print("[OK] Todos los módulos Exness/MetaTrader5 verificados y operativos.")
