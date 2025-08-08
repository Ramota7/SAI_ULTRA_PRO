
import numpy as np

class MultiTimeframeValidator:
    """
    Valida una señal en el timeframe base y confirma tendencia y estructura en 2 timeframes superiores.
    """
    def __init__(self, symbol, base_tf='15m'):
        self.symbol = symbol
        self.base_tf = base_tf
        self.superiores = self.get_superiores(base_tf)

    def get_superiores(self, base_tf):
        # Define la jerarquía de timeframes
        orden = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        idx = orden.index(base_tf) if base_tf in orden else 2
        # Devuelve los dos timeframes superiores
        return [orden[i] for i in range(idx+1, min(idx+3, len(orden)))]

    def obtener_candles(self, tf, limit=200):
        import requests
        url = f'https://fapi.binance.com/fapi/v1/klines?symbol={self.symbol}&interval={tf}&limit={limit}'
        r = requests.get(url)
        return np.array(r.json(), dtype=object)

    def detectar_tendencia(self, candles):
        # Tendencia simple: compara cierre actual vs cierre N velas atrás
        close = candles[:,4].astype(float)
        if len(close) < 30:
            return 'indefinida'
        if close[-1] > close[-20]:
            return 'alcista'
        elif close[-1] < close[-20]:
            return 'bajista'
        else:
            return 'lateral'

    def detectar_estructura(self, candles):
        # Estructura simple: BOS (Break of Structure)
        highs = candles[:,2].astype(float)
        lows = candles[:,3].astype(float)
        close = candles[:,4].astype(float)
        prev_high = highs[-3]
        prev_low = lows[-3]
        last_close = close[-2]
        bos_alcista = last_close > prev_high
        bos_bajista = last_close < prev_low
        if bos_alcista:
            return 'alcista'
        elif bos_bajista:
            return 'bajista'
        else:
            return 'lateral'

    def validar(self, tipo_entrada):
        """
        tipo_entrada: 'compra' o 'venta' (o 'long'/'short')
        Retorna True si la tendencia y estructura en ambos timeframes superiores confirman la señal.
        """
        for tf in self.superiores:
            candles = self.obtener_candles(tf)
            tendencia = self.detectar_tendencia(candles)
            estructura = self.detectar_estructura(candles)
            if tipo_entrada in ['compra', 'long']:
                if tendencia != 'alcista' or estructura != 'alcista':
                    return False
            elif tipo_entrada in ['venta', 'short']:
                if tendencia != 'bajista' or estructura != 'bajista':
                    return False
        return True
