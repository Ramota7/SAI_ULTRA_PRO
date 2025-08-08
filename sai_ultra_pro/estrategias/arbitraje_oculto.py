
import requests
import time
import json

class ArbitrajeOculto:
    def __init__(self):
        self.symbol_binance = 'BTCUSDT'  # Puede parametrizarse
        self.symbol_exness = 'BTCUSD'    # Puede parametrizarse
        self.size = 0.01                 # Tamaño sugerido (puede parametrizarse)
        self.latencia_max = 2            # segundos
        self.config = self.cargar_config()
        self.spread_min = self.config.get('spread_min', 0.003)

    def cargar_config(self):
        try:
            with open('sai_ultra_pro/config/config.json') as f:
                return json.load(f)
        except:
            return {}

    def precio_binance(self):
        url = f'https://api.binance.com/api/v3/ticker/bookTicker?symbol={self.symbol_binance}'
        r = requests.get(url)
        data = r.json()
        return float(data['bidPrice']), float(data['askPrice'])

    def precio_exness(self):
        # Simulación: en real usar API de Exness
        # Aquí se simula con un pequeño spread respecto a Binance
        binance_bid, binance_ask = self.precio_binance()
        exness_bid = binance_bid * (1 + 0.004)  # simula diferencia
        exness_ask = binance_ask * (1 + 0.004)
        return exness_bid, exness_ask

    def verificar_liquidez(self, broker, size):
        # Simulación: en real consultar orderbook
        return True

    def estimar_latencia(self, broker):
        # Simulación: en real medir tiempo de respuesta
        return 1.0

    def ia_confirmacion(self):
        binance_bid, binance_ask = self.precio_binance()
        exness_bid, exness_ask = self.precio_exness()
        # Oportunidad: comprar barato y vender caro
        spread_buy_binance = (exness_bid - binance_ask) / binance_ask
        spread_buy_exness = (binance_bid - exness_ask) / exness_ask
        self.señal = None
        if spread_buy_binance > self.spread_min:
            if self.verificar_liquidez('binance', self.size) and self.verificar_liquidez('exness', self.size):
                lat_binance = self.estimar_latencia('binance')
                lat_exness = self.estimar_latencia('exness')
                if lat_binance < self.latencia_max and lat_exness < self.latencia_max:
                    beneficio = (exness_bid - binance_ask) * self.size
                    self.señal = {
                        'comprar_en': 'Binance',
                        'vender_en': 'Exness',
                        'par': self.symbol_binance,
                        'size': self.size,
                        'potencial_beneficio': round(beneficio, 2),
                        'spread': round(spread_buy_binance*100, 2),
                        'tiempo_valido': self.latencia_max,
                        'razon': 'Arbitraje positivo Binance→Exness'
                    }
                    return True
        if spread_buy_exness > self.spread_min:
            if self.verificar_liquidez('exness', self.size) and self.verificar_liquidez('binance', self.size):
                lat_binance = self.estimar_latencia('binance')
                lat_exness = self.estimar_latencia('exness')
                if lat_binance < self.latencia_max and lat_exness < self.latencia_max:
                    beneficio = (binance_bid - exness_ask) * self.size
                    self.señal = {
                        'comprar_en': 'Exness',
                        'vender_en': 'Binance',
                        'par': self.symbol_binance,
                        'size': self.size,
                        'potencial_beneficio': round(beneficio, 2),
                        'spread': round(spread_buy_exness*100, 2),
                        'tiempo_valido': self.latencia_max,
                        'razon': 'Arbitraje positivo Exness→Binance'
                    }
                    return True
        return False

    def ejecutar(self, gestor):
        if hasattr(self, 'señal') and self.señal:
            return {
                'estrategia': 'ArbitrajeOculto',
                'señal': self.señal,
                'resultado': 'pendiente'
            }
        return {'estrategia': 'ArbitrajeOculto', 'resultado': 'sin señal'}
