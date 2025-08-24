"""Gateway de órdenes con circuit breaker ligero.

Provee funciones para decidir si permitir una orden y para registrar
el resultado (éxito/fracaso). Persistencia mínima en `artifacts/circuit_breaker.json`.
"""
from __future__ import annotations
import os
import time
import json
from typing import Dict, Any

ROOT = os.getcwd()
ARTIFACTS = os.path.join(ROOT, 'artifacts')
os.makedirs(ARTIFACTS, exist_ok=True)
STATE_FILE = os.path.join(ARTIFACTS, 'circuit_breaker.json')

# Configurables via env
THRESHOLD = int(os.getenv('CB_THRESHOLD', '3'))          # fallos para abrir
WINDOW_S = int(os.getenv('CB_WINDOW_S', '300'))          # ventana para contar fallos
OPEN_S = int(os.getenv('CB_OPEN_S', '600'))              # tiempo en abierto


def _now() -> float:
    return time.time()


def _load_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state: Dict[str, Any]):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def _key(broker: str, symbol: str) -> str:
    return f"{broker}:{symbol}"


def order_allowed(broker: str, symbol: str) -> bool:
    """Devuelve True si el gateway permite enviar la orden actualmente."""
    state = _load_state()
    k = _key(broker, symbol)
    entry = state.get(k, {})
    open_until = entry.get('open_until', 0)
    now = _now()
    if open_until and now < open_until:
        return False
    return True


def record_order_result(broker: str, symbol: str, success: bool):
    """Registrar resultado: en caso de fallo actualizar contador y abrir breaker si toca."""
    state = _load_state()
    k = _key(broker, symbol)
    entry = state.get(k, {'failures': [], 'open_until': 0})
    now = _now()
    # limpiar fallos antiguos
    entry['failures'] = [t for t in entry.get('failures', []) if now - t <= WINDOW_S]

    if success:
        # en éxito, reducir historial (opcional: limpiar)
        entry['failures'] = []
        entry['open_until'] = 0
    else:
        entry.setdefault('failures', []).append(now)
        # comprobar threshold
        if len(entry['failures']) >= THRESHOLD:
            entry['open_until'] = now + OPEN_S
            entry['failures'] = []

    state[k] = entry
    _save_state(state)


def get_status(broker: str, symbol: str) -> Dict[str, Any]:
    state = _load_state()
    k = _key(broker, symbol)
    entry = state.get(k, {'failures': [], 'open_until': 0})
    now = _now()
    return {
        'broker': broker,
        'symbol': symbol,
        'failures_count': len(entry.get('failures', [])),
        'open_until': entry.get('open_until', 0),
        'open': bool(entry.get('open_until', 0) and now < entry.get('open_until', 0))
    }
