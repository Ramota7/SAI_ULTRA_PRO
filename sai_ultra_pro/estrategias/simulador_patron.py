import numpy as np
import pandas as pd

class SimuladorPatron:
    """
    Simula la señal/patrón en los últimos 1000 datos y calcula el win rate.
    Solo permite operar si el win rate es mayor al 60%.
    """
    def __init__(self, symbol, timeframe, patron_func, data_path=None):
        self.symbol = symbol
        self.timeframe = timeframe
        self.patron_func = patron_func  # función que detecta la señal/patrón
        self.data_path = data_path or f'sai_ultra_pro/ia/data_{symbol}_{timeframe}.csv'

    def cargar_datos(self):
        try:
            df = pd.read_csv(self.data_path)
            if len(df) > 1000:
                df = df.iloc[-1000:]
            return df
        except Exception as e:
            print(f'[SimuladorPatron] Error cargando datos: {e}')
            return None

    def simular(self):
        df = self.cargar_datos()
        if df is None or len(df) < 50:
            return 0.0, 0
        resultados = []
        for i in range(20, len(df)-6):
            sub = df.iloc[:i+1]
            señal = self.patron_func(sub)
            if señal:
                entrada = señal.get('entrada', None)
                stop = señal.get('stop', None)
                target = señal.get('target', None) or señal.get('objetivo', None)
                tipo = señal.get('tipo')
                if entrada is None or stop is None or target is None or tipo is None:
                    continue
                futuros = df.iloc[i+1:i+6]  # próximas 5 velas
                hit = None
                for idx, row in futuros.iterrows():
                    high = row['high'] if 'high' in row else row[-2]
                    low = row['low'] if 'low' in row else row[-1]
                    # LONG/COMPRA: primero stop, luego target
                    if tipo in ['long', 'compra']:
                        if low <= stop:
                            hit = 0
                            break
                        if high >= target:
                            hit = 1
                            break
                    # SHORT/VENTA: primero stop, luego target
                    elif tipo in ['short', 'venta']:
                        if high >= stop:
                            hit = 0
                            break
                        if low <= target:
                            hit = 1
                            break
                if hit is not None:
                    resultados.append(hit)
        if not resultados:
            return 0.0, 0
        winrate = 100 * sum(resultados) / len(resultados)
        return winrate, len(resultados)

    def validar_operacion(self):
        winrate, n = self.simular()
        print(f'[SimuladorPatron] Winrate: {winrate:.1f}% en {n} señales simuladas')
        return winrate > 60 and n > 10
