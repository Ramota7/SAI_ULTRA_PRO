import json
import sys
from datetime import datetime

def verificar_binance():
    try:
        import requests, time, hmac, hashlib
        with open('sai_ultra_pro/config/config.json', 'r') as f:
            config = json.load(f)
        api_key = config['api_keys']['BINANCE_API_KEY']
        api_secret = config['api_keys']['BINANCE_API_SECRET']
        timestamp = int(time.time() * 1000)
        query_string = f'timestamp={timestamp}'
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        params = {
            'timestamp': timestamp,
            'signature': signature
        }
        headers = {
            'X-MBX-APIKEY': api_key
        }
        url = 'https://api.binance.com/api/v3/account'
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            saldo_total = sum(float(asset['free']) + float(asset['locked']) for asset in data.get('balances', []))
            print(f"[BINANCE] Conexión exitosa. Saldo total: {saldo_total:.2f}")
            return True
        else:
            error_msg = f"[BINANCE][ERROR] {r.text}"
            print(error_msg)
            registrar_error_log(error_msg)
            sys.exit(1)
    except Exception as e:
        error_msg = f"[BINANCE][ERROR] Excepción: {e}"
        print(error_msg)
        registrar_error_log(error_msg)
        sys.exit(1)

def verificar_exness():
    try:
        import MetaTrader5 as mt5
        with open('sai_ultra_pro/config/config.json', 'r') as f:
            config = json.load(f)
        login = config['api_keys'].get('EXNESS_LOGIN') or config['api_keys'].get('EXNESS_API_KEY')
        password = config['api_keys'].get('EXNESS_PASSWORD') or config['api_keys'].get('EXNESS_API_SECRET')
        server = config['api_keys']['EXNESS_SERVER']
        if not mt5.initialize(login=int(login), password=password, server=server):
            error_msg = f"[EXNESS][ERROR] No se pudo conectar: {mt5.last_error()}"
            print(error_msg)
            registrar_error_log(error_msg)
            sys.exit(1)
        info = mt5.account_info()
        if info:
            print(f"[EXNESS] Conexión exitosa. Balance: {info.balance:.2f}")
            mt5.shutdown()
            return True
        else:
            error_msg = "[EXNESS][ERROR] No se pudo obtener info de cuenta."
            print(error_msg)
            registrar_error_log(error_msg)
            mt5.shutdown()
            sys.exit(1)
    except Exception as e:
        error_msg = f"[EXNESS][ERROR] Excepción: {e}"
        print(error_msg)
        registrar_error_log(error_msg)
        sys.exit(1)

def registrar_error_log(msg):
    with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
        flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")

def verificar_credenciales():
    ok_binance = verificar_binance()
    ok_exness = verificar_exness()
    if ok_binance and ok_exness:
        print('✅ Verificación de credenciales completada con éxito.')

if __name__ == "__main__":
    verificar_credenciales()
