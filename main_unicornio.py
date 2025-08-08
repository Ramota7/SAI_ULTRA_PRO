# main_unicornio.py
# Punto de entrada del bot unicornio auto-mejorable y multiplataforma
from core.engine import Engine


import sys
def main():
    print("[UNICORNIO] Iniciando bot auto-mejorable y multiplataforma...")
    engine = Engine()
    if len(sys.argv) > 1 and sys.argv[1] == "--validar":
        engine.run(validar=True)
    else:
        engine.run()

if __name__ == "__main__":
    main()
