
import requests
import numpy as np
import json

class AnalizadorVolatilidad:
    def __init__(self):
        self.symbol = 'BTCUSDT'  # Puede parametrizarse
        self.timeframe = '15m'
        self.config = self.cargar_config()
        self.umbral_volatilidad = self.config.get('umbral_volatilidad', 0.012)
        self.umbral_volumen = self.config.get('umbral_volumen', 2.0)

    def cargar_config(self):
        try:
            with open('sai_ultra_pro/config/config.json') as f:
                return json.load(f)
        except:
            return {}

    def encontrar_limit_maximo(self, limit_inicial=1500, limit_min=100, paso=100):
        limit = limit_inicial
        while limit >= limit_min:
            url = f'https://fapi.binance.com/fapi/v1/klines?symbol={self.symbol}&interval={self.timeframe}&limit={limit}'
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

    def obtener_candles(self, limit=None):
        if limit is None:
            print(f"[INFO] Buscando limit máximo permitido para {self.symbol} {self.timeframe}...")
            limit = self.encontrar_limit_maximo()
            print(f"[INFO] Usando limit={limit}")
        url = f'https://fapi.binance.com/fapi/v1/klines?symbol={self.symbol}&interval={self.timeframe}&limit={limit}'
        r = requests.get(url)
        return np.array(r.json(), dtype=object)

    def evaluar_entorno(self):
        candles = self.obtener_candles()
        close = candles[:,4].astype(float)
        open_ = candles[:,1].astype(float)
        volume = candles[:,5].astype(float)
        # Volatilidad: rango relativo de cada vela
        rangos = np.abs(close - open_) / close
        volat_media = np.mean(rangos)
        desv = np.std(rangos)
        # Velas extremas
        velas_extremas = np.sum(rangos > (volat_media + 2*desv))
        # Cambios bruscos de volumen
        vol_media = np.mean(volume)
        cambios_vol = np.sum(volume > (vol_media * self.umbral_volumen))
        # Decisión
        if volat_media > self.umbral_volatilidad or velas_extremas > 0 or cambios_vol > 0:
            return 'riesgo alto'
        else:
            return 'entorno favorable'

    def es_dia_seguro(self):
        return self.evaluar_entorno() == 'entorno favorable'
