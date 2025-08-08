
import requests
import numpy as np

class LiquidezBallena:
    def __init__(self):
        self.symbol = 'BTCUSDT'  # Puede parametrizarse
        self.timeframe = '15m'

    def obtener_candles(self, limit=200):
        url = f'https://fapi.binance.com/fapi/v1/klines?symbol={self.symbol}&interval={self.timeframe}&limit={limit}'
        r = requests.get(url)
        return np.array(r.json(), dtype=object)

    def detectar_zonas_liquidez(self, candles):
        # Busca mínimos/máximos iguales (acumulación de liquidez)
        lows = candles[:,3].astype(float)
        highs = candles[:,2].astype(float)
        zonas_min = []
        zonas_max = []
        for i in range(10, len(lows)-5):
            if all(abs(lows[i] - lows[i-j]) < 0.05 for j in range(1,4)):
                zonas_min.append((i, lows[i]))
            if all(abs(highs[i] - highs[i-j]) < 0.05 for j in range(1,4)):
                zonas_max.append((i, highs[i]))
        return zonas_min, zonas_max

    def sweep_y_reversion(self, candles, zonas_min, zonas_max):
        close = candles[:,4].astype(float)
        open_ = candles[:,1].astype(float)
        high = candles[:,2].astype(float)
        low = candles[:,3].astype(float)
        volume = candles[:,5].astype(float)
        señal = None
        razon = "Trampa institucional"
        for idx, zona in zonas_min:
            # Sweep bajista: rompe mínimo con vela fuerte y volumen anormal
            if low[idx+1] < zona and volume[idx+1] > np.mean(volume[-30:])*1.5:
                # Reversión rápida: pinbar o engulfing alcista
                cuerpo = abs(close[idx+1] - open_[idx+1])
                mecha = (close[idx+1] - low[idx+1]) > cuerpo*2
                engulfing = close[idx+2] > open_[idx+2] and close[idx+2] > close[idx+1]
                if mecha or engulfing:
                    stop = low[idx+1] - 0.1
                    entrada = close[idx+2]
                    riesgo = abs(entrada - stop)
                    target = round(entrada + riesgo*2.5, 2)
                    señal = {
                        'tipo': 'long',
                        'par': self.symbol,
                        'timeframe': self.timeframe,
                        'entrada': entrada,
                        'stop': stop,
                        'target': target,
                        'razon': razon
                    }
                    break
        for idx, zona in zonas_max:
            # Sweep alcista: rompe máximo con vela fuerte y volumen anormal
            if high[idx+1] > zona and volume[idx+1] > np.mean(volume[-30:])*1.5:
                # Reversión rápida: pinbar o engulfing bajista
                cuerpo = abs(close[idx+1] - open_[idx+1])
                mecha = (high[idx+1] - close[idx+1]) > cuerpo*2
                engulfing = close[idx+2] < open_[idx+2] and close[idx+2] < close[idx+1]
                if mecha or engulfing:
                    stop = high[idx+1] + 0.1
                    entrada = close[idx+2]
                    riesgo = abs(stop - entrada)
                    target = round(entrada - riesgo*2.5, 2)
                    señal = {
                        'tipo': 'short',
                        'par': self.symbol,
                        'timeframe': self.timeframe,
                        'entrada': entrada,
                        'stop': stop,
                        'target': target,
                        'razon': razon
                    }
                    break
        return señal

    def ia_confirmacion(self):
        candles = self.obtener_candles()
        zonas_min, zonas_max = self.detectar_zonas_liquidez(candles)
        self.señal = self.sweep_y_reversion(candles, zonas_min, zonas_max)
        return self.señal is not None

    def ejecutar(self, gestor):
        if hasattr(self, 'señal') and self.señal:
            return {
                'estrategia': 'LiquidezBallena',
                'señal': self.señal,
                'resultado': 'pendiente'
            }
        return {'estrategia': 'LiquidezBallena', 'resultado': 'sin señal'}
