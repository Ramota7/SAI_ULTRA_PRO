from sai_ultra_pro.main import ejecutar_orden_exness

# Parámetros de prueba
api_key = '195762110'
api_secret = 'A2508m***'  # Reemplaza por el real si es necesario
server = 'Exness-MT5Real11'
platform = 'mt5'
symbol = 'XAUUSDm'

resultado = ejecutar_orden_exness('long', 0.01, api_key, api_secret, server, platform, symbol=symbol)
print(f"Resultado ejecución Exness: {resultado}")
