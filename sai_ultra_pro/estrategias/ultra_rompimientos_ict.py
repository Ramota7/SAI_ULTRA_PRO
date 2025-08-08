

import requests
import numpy as np
from tensorflow.keras.models import load_model
import shap
import os


class UltraRompimientosICT:

    def __init__(self):
        import json
        self.timeframes = ['15m', '1h', '4h']
        self.symbol = 'BTCUSDT'  # Puede parametrizarse
        self.modelo_ia = self.cargar_modelo_ia()
        # Cargar umbral desde config.json
        try:
            with open('sai_ultra_pro/config/config.json') as f:
                config = json.load(f)
            self.umbral_ia = config.get('umbral_ia', 0.6)
        except:
            self.umbral_ia = 0.6

    def cargar_modelo_ia(self):
        ruta = os.path.join(os.path.dirname(__file__), '../ia/modelo_transformer.h5')
        ruta = os.path.abspath(ruta)
        if os.path.exists(ruta):
            try:
                modelo = load_model(ruta)
                print('[IA] Modelo Transformer cargado correctamente')
                return modelo
            except Exception as e:
                print(f'[IA] Error al cargar modelo: {e}')
        else:
            print('[IA] Modelo Transformer no encontrado, se usará validación simple')
        return None

    def obtener_candles(self, tf, limit=200):
        url = f'https://fapi.binance.com/fapi/v1/klines?symbol={self.symbol}&interval={tf}&limit={limit}'
        r = requests.get(url)
        return np.array(r.json(), dtype=object)

    def detectar_bos(self, candles):
        # Detecta ruptura de estructura (BOS) simple: último alto/bajo roto
        highs = candles[:,2].astype(float)
        lows = candles[:,3].astype(float)
        close = candles[:,4].astype(float)
        prev_high = highs[-3]
        prev_low = lows[-3]
        last_close = close[-2]
        bos_alcista = last_close > prev_high
        bos_bajista = last_close < prev_low
        return bos_alcista, bos_bajista, prev_high, prev_low, last_close

    def barrido_liquidez(self, candles):
        # Busca mecha que barra el alto/bajo anterior antes del BOS
        highs = candles[:,2].astype(float)
        lows = candles[:,3].astype(float)
        close = candles[:,4].astype(float)
        prev_high = highs[-4]
        prev_low = lows[-4]
        wick_high = highs[-3]
        wick_low = lows[-3]
        barrido_alcista = wick_high > prev_high and close[-3] < wick_high
        barrido_bajista = wick_low < prev_low and close[-3] > wick_low
        return barrido_alcista, barrido_bajista

    def validar_fvg_ob(self, candles):
        # Busca FVG (Fair Value Gap) u Order Block en últimas 5 velas
        close = candles[:,4].astype(float)
        open_ = candles[:,1].astype(float)
        fvg = False
        ob = False
        for i in range(-6, -1):
            gap = abs(open_[i+1] - close[i])
            if gap > (0.001 * close[i]):
                fvg = True
            # Order Block: vela grande contraria antes del movimiento
            body = abs(close[i] - open_[i])
            if body > (0.005 * close[i]):
                ob = True
        return fvg or ob


    def ia_confirmacion(self):
        # Confirmación IA: Order Blocks, BOS, Liquidez falsa + validación IA
        for tf in self.timeframes:
            candles = self.obtener_candles(tf)
            bos_alcista, bos_bajista, prev_high, prev_low, last_close = self.detectar_bos(candles)
            barrido_alcista, barrido_bajista = self.barrido_liquidez(candles)
            fvg_ob = self.validar_fvg_ob(candles)
            # Si cumple condiciones técnicas, validar con IA si hay modelo
            if (bos_alcista and barrido_alcista and fvg_ob) or (bos_bajista and barrido_bajista and fvg_ob):
                entrada = last_close
                stop = prev_low if bos_alcista else prev_high
                tipo = 'compra' if bos_alcista else 'venta'
                objetivo = round((last_close - prev_low) * 3 + last_close, 2) if bos_alcista else round(last_close - (prev_high - last_close) * 3, 2)
                # Validación IA
                if self.modelo_ia is not None:
                    closes = candles[-10:,4].astype(float)
                    x = (closes - closes.mean()) / (closes.std() + 1e-8)
                    x = x.reshape((1, x.shape[0], 1))
                    prob = float(self.modelo_ia.predict(x)[0][0])
                    print(f'[IA] Probabilidad de éxito según modelo: {prob:.2f}')
                    # Explicabilidad con SHAP (opcional, solo para debug)
                    try:
                        explainer = shap.Explainer(self.modelo_ia, x)
                        shap_values = explainer(x)
                        print(f'[IA][SHAP] Importancia features: {shap_values.values}')
                    except Exception as e:
                        print(f'[IA][SHAP] No se pudo calcular SHAP: {e}')
                    if prob < self.umbral_ia:
                        continue  # Señal no validada por IA
                self.señal = {
                    'tipo': tipo,
                    'objetivo': objetivo,
                    'stop': stop,
                    'entrada': entrada,
                    'timeframe': tf
                }
                return True
        return False

    def ejecutar(self, gestor):
        # Devuelve la señal generada
        if hasattr(self, 'señal'):
            return {
                'estrategia': 'UltraRompimientosICT',
                'señal': self.señal,
                'resultado': 'pendiente'
            }
        return {'estrategia': 'UltraRompimientosICT', 'resultado': 'sin señal'}
