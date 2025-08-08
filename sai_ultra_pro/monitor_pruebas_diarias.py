import time
import json
from datetime import datetime
from integracion.telegram_alertas import enviar_alerta
from main import validar_api_binance, validar_api_exness
from ia.analizador_volatilidad import AnalizadorVolatilidad
from ia.analizador_volatilidad_exness import AnalizadorVolatilidadExness

CONFIG_PATH = 'sai_ultra_pro/config/config.json'


def prueba_diaria():
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    # Prueba conexión Binance
    try:
        api_binance = config['api_keys']['BINANCE_API_KEY']
        api_binance_secret = config['api_keys']['BINANCE_API_SECRET']
        ok_binance = validar_api_binance(api_binance, api_binance_secret)
        if not ok_binance:
            enviar_alerta('[MONITOREO] Falla de conexión con Binance')
    except Exception as e:
        enviar_alerta(f'[MONITOREO] Error conexión Binance: {e}')
    # Prueba conexión Exness
    try:
        api_exness = config['api_keys']['EXNESS_API_KEY']
        api_exness_secret = config['api_keys']['EXNESS_API_SECRET']
        server = config['api_keys']['EXNESS_SERVER']
        platform = config['api_keys']['EXNESS_PLATFORM']
        ok_exness = validar_api_exness(api_exness, api_exness_secret, server, platform)
        if not ok_exness:
            enviar_alerta('[MONITOREO] Falla de conexión con Exness')
    except Exception as e:
        enviar_alerta(f'[MONITOREO] Error conexión Exness: {e}')
    # Prueba entorno Binance
    try:
        activos = config.get('activos', ['BTCUSDT'])
        for symbol in activos:
            av = AnalizadorVolatilidad()
            av.symbol = symbol
            entorno = av.evaluar_entorno()
            if entorno == 'riesgo alto':
                enviar_alerta(f'[MONITOREO] Entorno de riesgo alto en Binance para {symbol}')
    except Exception as e:
        enviar_alerta(f'[MONITOREO] Error entorno Binance: {e}')
    # Prueba entorno Exness
    try:
        symbols_exness = ['USDRUB', 'USDAED', 'USDBRL', 'US30m', 'US500m', 'USTECm']
        for symbol in symbols_exness:
            avx = AnalizadorVolatilidadExness(symbol=symbol)
            entorno = avx.evaluar_entorno()
            if entorno == 'riesgo alto':
                enviar_alerta(f'[MONITOREO] Entorno de riesgo alto en Exness para {symbol}')
    except Exception as e:
        enviar_alerta(f'[MONITOREO] Error entorno Exness: {e}')
    # Auditoría de claves API
    try:
        with open('sai_ultra_pro/ia/api_audit.log', 'a') as f:
            f.write(f'{datetime.now()} | Auditoría de claves OK\n')
        # Aquí puedes agregar lógica de rotación/alerta si no se han rotado en 30 días
    except Exception as e:
        enviar_alerta(f'[MONITOREO] Error auditoría de claves: {e}')

if __name__ == "__main__":
    prueba_diaria()
