"""Módulo de seguridad ligero.

Controla si se permiten operaciones reales en tiempo de ejecución usando
variables de entorno. Está diseñado para evitar ejecuciones accidentales
de órdenes en entornos de desarrollo o CI.

Uso:
  - Establece ALLOW_REAL_TRADES=1 para permitir operaciones reales.
  - De lo contrario, las funciones de orden deben operar en modo observación.
"""
import os


def allow_real_trades() -> bool:
    """Devuelve True si la variable de entorno ALLOW_REAL_TRADES habilita trades reales.

    Por seguridad el valor por defecto es deshabilitado.
    """
    v = os.getenv('ALLOW_REAL_TRADES', '')
    return v in ('1', 'true', 'True', 'yes', 'YES')


def require_supervisor_token(provided_token: str | None) -> bool:
    """Comprueba (si existe) la igualdad con SUPERVISOR_CONTROL_TOKEN.

    Si no hay token configurado en el entorno, devuelve False.
    Esta función sólo es una utilidad ligera; no pretende sustituir
    mecanismos robustos de autenticación.
    """
    sup = os.getenv('SUPERVISOR_CONTROL_TOKEN')
    if not sup:
        return False
    return bool(provided_token) and (provided_token == sup)
