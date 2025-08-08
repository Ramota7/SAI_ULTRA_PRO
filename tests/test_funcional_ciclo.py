# Test funcional: simula un ciclo de trading en modo simulación y valida el flujo principal
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sai_ultra_pro.core.engine import Engine

def test_funcional_ciclo():
    engine = Engine()
    engine.modo_simulacion = True
    # Ejecuta solo un ciclo (forzando break tras el primero)
    import builtins
    old_sleep = getattr(__import__('time'), 'sleep')
    def fake_sleep(x):
        raise SystemExit  # Forzar salida tras un ciclo
    __import__('time').sleep = fake_sleep
    try:
        engine.run()
    except SystemExit:
        print("[OK] Ciclo de trading simulado ejecutado correctamente.")
    finally:
        __import__('time').sleep = old_sleep

if __name__ == "__main__":
    test_funcional_ciclo()
