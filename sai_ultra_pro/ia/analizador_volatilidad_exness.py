import MetaTrader5 as mt5
import numpy as np
import pandas as pd
import json

class AnalizadorVolatilidadExness:
    def __init__(self, symbol='USDRUB', timeframe=mt5.TIMEFRAME_M15, n=100):
        self.symbol = symbol
        self.timeframe = timeframe
        self.n = n
        self.config = self.cargar_config()
        self.umbral_volatilidad = self.config.get('umbral_volatilidad', 0.012)
        self.umbral_volumen = self.config.get('umbral_volumen', 2.0)

    def cargar_config(self):
        try:
            with open('sai_ultra_pro/config/config.json') as f:
                return json.load(f)
        except:
            return {}

    def obtener_candles(self):
        if not mt5.initialize():
            print('[ERROR] No se pudo inicializar MetaTrader5')
            return None
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, self.n)
        mt5.shutdown()
        if rates is None:
            print(f'[ERROR] No se pudo obtener rates para {self.symbol}')
            return None
        df = pd.DataFrame(rates)
        return df

    def evaluar_entorno(self):
        df = self.obtener_candles()
        if df is None or len(df) < 20:
            return 'desconocido'
        close = df['close'].values
        open_ = df['open'].values
        volume = df['tick_volume'].values
        rangos = np.abs(close - open_) / close
        volat_media = np.mean(rangos)
        desv = np.std(rangos)
        velas_extremas = np.sum(rangos > (volat_media + 2*desv))
        vol_media = np.mean(volume)
        cambios_vol = np.sum(volume > (vol_media * self.umbral_volumen))
        if volat_media > self.umbral_volatilidad or velas_extremas > 0 or cambios_vol > 0:
            return 'riesgo alto'
        else:
            return 'entorno favorable'

    def es_dia_seguro(self):
        return self.evaluar_entorno() == 'entorno favorable'
