"""Wrapper seguro para enviar órdenes a brokers.

Provee: send_order(broker, side, symbol, qty, **kwargs)

Comportamiento:
- Respeta modo observación (no envía si MODO_OBSERVACION activa).
- Comprueba circuit breaker (`order_allowed`) antes de enviar.
- Registra resultado en `record_order_result`.
- Permite retries limitadas.
"""
from __future__ import annotations
import os
import time
from typing import Any


def send_order(broker: str, side: str, symbol: str, qty: float, retries: int = 1, **kwargs) -> Any:
    """Enviar orden de forma segura. Devuelve el resultado del broker o None si no enviado."""
    # import dinámico para respetar reimports en tests y lectura de MODO_OBSERVACION
    try:
        from sai_ultra_pro import main as main_mod
        from sai_ultra_pro.orders import gateway
    except Exception as e:
        # módulos faltantes -> no enviar
        print(f"[SAFE_ORDER] import error: {e}")
        return None

    # Modo observación global
    try:
        if getattr(main_mod, 'MODO_OBSERVACION', True):
            print(f"[SAFE_ORDER] MODO_OBSERVACION activo — no se envía orden {broker} {side} {symbol}")
            return None
    except Exception:
        return None

    # Circuit breaker
    try:
        if not gateway.order_allowed(broker, symbol):
            print(f"[SAFE_ORDER] Circuit breaker abierto para {broker}:{symbol}")
            return None
    except Exception:
        # si falla el checker, no bloquear por seguridad
        pass

    # Mapear a función específica
    send_fn = None
    if broker.lower() == 'binance':
        if side.lower() in ('buy', 'long'):
            def send_fn():
                from sai_ultra_pro.main import enviar_orden_binance
                return enviar_orden_binance(kwargs.get('api_key'), kwargs.get('api_secret'), symbol, qty)
        else:
            def send_fn():
                from sai_ultra_pro.main import enviar_orden_venta_binance
                return enviar_orden_venta_binance(kwargs.get('api_key'), kwargs.get('api_secret'), symbol, qty)
    elif broker.lower() == 'exness':
        def send_fn():
            from sai_ultra_pro.main import ejecutar_orden_exness
            señal = 'long' if side.lower() in ('buy', 'long') else 'short'
            return ejecutar_orden_exness(señal, qty, kwargs.get('api_key'), kwargs.get('api_secret'), server=kwargs.get('server'), platform=kwargs.get('platform'), symbol=symbol, price=kwargs.get('price'), sl=kwargs.get('sl'), tp=kwargs.get('tp'))
    else:
        print(f"[SAFE_ORDER] Broker no soportado: {broker}")
        return None

    # Intentar enviar con retries
    attempt = 0
    while attempt <= retries:
        attempt += 1
        try:
            res = send_fn()
            # decidir éxito: None/False = fallo, cualquier otra cosa = éxito
            success = not (res is None or res is False)
            try:
                gateway.record_order_result(broker, symbol, success)
            except Exception:
                pass
            return res
        except Exception as e:
            print(f"[SAFE_ORDER] Error en envío intento {attempt}: {e}")
            try:
                gateway.record_order_result(broker, symbol, False)
            except Exception:
                pass
            if attempt > retries:
                return None
            time.sleep(0.1)
