import requests
import numpy as np
import time

class TrailingTakeProfit:
    def __init__(self, symbol, entrada, stop, target, tipo='long', freq=10):
        self.symbol = symbol
        self.entrada = entrada
        self.stop = stop
        self.target = target
        self.tipo = tipo
        self.freq = freq  # segundos entre consultas
        self.r = abs(entrada - stop)
        self.trailing = stop
        self.salida_parcial = False
        self.salida_total = False

    def obtener_precio_y_volumen(self):
        url = f'https://api.binance.com/api/v3/klines?symbol={self.symbol}&interval=1m&limit=5'
        try:
            r = requests.get(url)
            data = r.json()
            precios = np.array([float(c[4]) for c in data])  # cierre
            volumenes = np.array([float(c[5]) for c in data])
            return precios, volumenes
        except Exception:
            return np.array([]), np.array([])

    def calcular_impulso(self, precios, volumenes):
        if len(precios) < 2 or len(volumenes) < 2:
            return 1.0
        cambio_precio = (precios[-1] - precios[0]) / precios[0] if precios[0] != 0 else 0
        cambio_vol = (volumenes[-1] - volumenes[0]) / (volumenes[0]+1e-6)
        impulso = np.clip(abs(cambio_precio) * (1 + cambio_vol), 0, 1)
        return impulso

    def gestionar(self):
        while not self.salida_total:
            precios, volumenes = self.obtener_precio_y_volumen()
            if len(precios) == 0:
                time.sleep(self.freq)
                continue
            precio_actual = precios[-1]
            impulso = self.calcular_impulso(precios, volumenes)
            # Trailing stop desde 1R
            if self.tipo == 'long':
                if precio_actual >= self.entrada + self.r:
                    self.trailing = max(self.trailing, precio_actual - self.r)
                if precio_actual <= self.trailing:
                    self.salida_total = True
                    print(f"[TRAILING] Stop dinámico ejecutado en {precio_actual}")
                    break
                if not self.salida_parcial and precio_actual >= self.entrada + 2*self.r:
                    self.salida_parcial = True
                    print(f"[TRAILING] Toma parcial 2R en {precio_actual}")
                if impulso < 0.3 or precio_actual >= self.target:
                    self.salida_total = True
                    print(f"[TRAILING] Cierre total por impulso bajo o target en {precio_actual}")
                    break
            else:
                if precio_actual <= self.entrada - self.r:
                    self.trailing = min(self.trailing, precio_actual + self.r)
                if precio_actual >= self.trailing:
                    self.salida_total = True
                    print(f"[TRAILING] Stop dinámico ejecutado en {precio_actual}")
                    break
                if not self.salida_parcial and precio_actual <= self.entrada - 2*self.r:
                    self.salida_parcial = True
                    print(f"[TRAILING] Toma parcial 2R en {precio_actual}")
                if impulso < 0.3 or precio_actual <= self.target:
                    self.salida_total = True
                    print(f"[TRAILING] Cierre total por impulso bajo o target en {precio_actual}")
                    break
            time.sleep(self.freq)
