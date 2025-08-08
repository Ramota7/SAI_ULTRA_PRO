# Test para validar que todos los módulos principales importan correctamente
import importlib
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

MODULOS = [
    'sai_ultra_pro.main',
    'sai_ultra_pro.core.engine',
    'sai_ultra_pro.seguridad.protecciones',
    'sai_ultra_pro.estrategias.arbitraje_oculto',
    'sai_ultra_pro.estrategias.diversificacion',
    'sai_ultra_pro.ia.analizador_volatilidad',
    'sai_ultra_pro.integracion.telegram_alertas',
]

def test_imports():
    for mod in MODULOS:
        try:
            importlib.import_module(mod)
            print(f"[OK] Import {mod}")
        except Exception as e:
            print(f"[FAIL] Import {mod}: {e}")
            raise

if __name__ == "__main__":
    test_imports()
