"""Demo rápido del circuit breaker del gateway de órdenes.

Ejecutar desde la raíz del repo con: python tools/demo_circuit_breaker.py
Muestra cómo tras varios fallos el breaker abre y bloquea órdenes.
"""
import os
import sys
import time
import json

# Asegurar que el repo raíz esté en sys.path para imports locales
sys.path.insert(0, os.getcwd())

from sai_ultra_pro.orders import gateway


def clean_state():
    path = os.path.join(os.getcwd(), 'artifacts', 'circuit_breaker.json')
    try:
        if os.path.exists(path):
            os.remove(path)
            print('Estado anterior eliminado:', path)
    except Exception as e:
        print('No pude limpiar estado anterior:', e)


def pretty_print_status(broker, symbol):
    st = gateway.get_status(broker, symbol)
    print(json.dumps(st, indent=2))


def main():
    clean_state()
    broker = 'binance'
    symbol = 'BTCUSDT'

    print('Estado inicial:')
    pretty_print_status(broker, symbol)

    thr = int(os.getenv('CB_THRESHOLD', '3'))
    print(f'Generando {thr} fallos para abrir el breaker...')
    for i in range(thr):
        gateway.record_order_result(broker, symbol, success=False)
        print(f'  fallo {i+1}/{thr}')
        time.sleep(0.05)

    print('\nEstado tras fallos:')
    pretty_print_status(broker, symbol)

    allowed = gateway.order_allowed(broker, symbol)
    print('\norder_allowed =>', allowed)

    print('\nIntentando registrar éxito (no debería cerrar el breaker automáticamente si aún está abierto)...')
    gateway.record_order_result(broker, symbol, success=True)
    pretty_print_status(broker, symbol)


if __name__ == '__main__':
    main()
