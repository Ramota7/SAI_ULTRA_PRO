
import pandas as pd
import requests
import MetaTrader5 as mt5
import os
import time
from datetime import datetime

# --- Lógica de detección automática de limit (idéntica a entrenar_modelo.py) ---
def encontrar_limit_maximo(symbol='BTCUSDT', interval='15m', limit_inicial=1500, limit_min=100, paso=100):
    limit = limit_inicial
    while limit >= limit_min:
        url = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}'
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                print(f"[INFO] limit permitido: {limit}")
                return limit
            else:
                print(f"[WARN] limit={limit} no permitido: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"[ERROR] limit={limit} falló: {e}")
        limit -= paso
    print(f"[ERROR] No se encontró un valor válido de limit entre {limit_inicial} y {limit_min}")
    return limit_min

def descargar_binance(symbol, interval, limit=None):
    if limit is None:
        print(f"[INFO] Buscando limit máximo permitido para {symbol} {interval}...")
        limit = encontrar_limit_maximo(symbol, interval)
        print(f"[INFO] Usando limit={limit}")
    url = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}'
    r = requests.get(url)
    data = r.json()
    df = pd.DataFrame(data, columns=[
        'open_time','open','high','low','close','volume','close_time','qav','trades','taker_base_vol','taker_quote_vol','ignore'])
    df = df[['open_time','open','high','low','close','volume']].astype(float)
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    return df

def descargar_exness(symbol, timeframe=mt5.TIMEFRAME_M15, n=1000):
    if not mt5.initialize():
        print('Error al conectar con MetaTrader5')
        return None
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    mt5.shutdown()
    if rates is None:
        print('No se pudo descargar datos de Exness')
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df[['time','open','high','low','close','tick_volume']]

def marcar_noticias(df, news_times):
    df['noticia_macro'] = df['open_time'].isin(news_times)
    return df

def guardar_csv(df, nombre):
    ruta = os.path.join(os.path.dirname(__file__), nombre)
    df.to_csv(ruta, index=False)
    print(f'Datos guardados en {ruta}')

if __name__ == "__main__":
    activos = ['BTCUSDT','ETHUSDT','BNBUSDT']
    timeframes = ['15m','1h']
    for symbol in activos:
        for tf in timeframes:
            df = descargar_binance(symbol, tf, limit=None)
            guardar_csv(df, f'data_{symbol}_{tf}.csv')
    # Ejemplo Exness (requiere tener MetaTrader5 abierto y configurado)
    # df_ex = descargar_exness('EURUSD', mt5.TIMEFRAME_M15, 1000)
    # if df_ex is not None:
    #     guardar_csv(df_ex, 'data_EURUSD_15m_exness.csv')
