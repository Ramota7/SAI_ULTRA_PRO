# Test de cobertura de errores: fuerza errores en módulos críticos y valida manejo seguro
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta

def test_errores_telegram():
    print("[TEST] Forzando error de credenciales Telegram...")
    import json
    # Backup config
    config_path = 'sai_ultra_pro/config/config.json'
    with open(config_path) as f:
        data = json.load(f)
    backup = dict(data)
    data['api_keys']['TELEGRAM_BOT_TOKEN'] = ''
    data['api_keys']['TELEGRAM_CHAT_ID'] = ''
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=2)
    try:
        enviar_alerta("Mensaje que no debe enviarse")
    except Exception as e:
        print(f"[OK] Error capturado correctamente: {e}")
    finally:
        # Restaurar config
        with open(config_path, 'w') as f:
            json.dump(backup, f, indent=2)

def test_errores_import():
    print("[TEST] Forzando error de importación...")
    try:
        __import__('sai_ultra_pro.no_existe')
    except Exception as e:
        print(f"[OK] Error de importación capturado: {e}")

def test_errores_funcionales():
    print("[TEST] Forzando error funcional en ciclo de trading...")
    from sai_ultra_pro.core.engine import Engine
    engine = Engine()
    engine.modo_simulacion = True
    # Forzar error en el ciclo
    def fake_obtener_datos():
        raise RuntimeError("Error simulado en obtención de datos")
    engine.historicos.obtener_datos = fake_obtener_datos
    try:
        engine.run()
    except Exception as e:
        print(f"[OK] Error funcional capturado: {e}")

if __name__ == "__main__":
    test_errores_telegram()
    test_errores_import()
    test_errores_funcionales()
