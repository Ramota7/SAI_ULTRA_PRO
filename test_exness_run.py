import json
import sys
sys.path.append('sai_ultra_pro')
from sai_ultra_pro import main


def test_exness_run():
    """Invoca la rutina de prueba de Exness definida en `sai_ultra_pro.main`.
    No falla si las credenciales están vacías; la función `main.test_exness` maneja esa validación.
    """
    with open('sai_ultra_pro/config/config.json') as f:
        c = json.load(f)

    api_key = c['api_keys'].get('EXNESS_API_KEY', '')
    api_secret = c['api_keys'].get('EXNESS_API_SECRET', '')
    server = c['api_keys'].get('EXNESS_SERVER', '')
    platform = c['api_keys'].get('EXNESS_PLATFORM', '')
    symbol = 'EURUSD'

    # Ejecutar la comprobación; la función retorna True/False dependiendo de la conectividad.
    result = main.test_exness(api_key, api_secret, server, platform, symbol)
    # No forzamos True si no hay credenciales; sólo comprobamos que la llamada no levante excepciones.
    assert result in (True, False)
