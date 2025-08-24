"""Wrapper HTTP con sesión, retries y bloqueo de red por entorno.

Este módulo centraliza las llamadas HTTP para imponer timeouts, retries
y un interruptor global para deshabilitar la red en tests/CI.

Uso: from sai_ultra_pro.net.http import get, post, is_network_allowed
"""
from typing import Any, Dict
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_TIMEOUT = float(os.getenv('HTTP_DEFAULT_TIMEOUT', '5'))


def _create_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3, status_forcelist=(429, 500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retries)
    s.mount('http://', adapter)
    s.mount('https://', adapter)
    return s


_SESSION = _create_session()


def is_network_allowed() -> bool:
    """Devuelve False si la variable de entorno bloquea la red para tests.

Variables respetadas:
 - TEST_NO_NETWORK=1  (CI/tests)
 - NETWORK_DISABLED=1
"""
    if os.getenv('TEST_NO_NETWORK', '') in ('1', 'true', 'True'):
        return False
    if os.getenv('NETWORK_DISABLED', '') in ('1', 'true', 'True'):
        return False
    return True


def _ensure_network():
    if not is_network_allowed():
        raise RuntimeError('Network access disabled by environment (TEST_NO_NETWORK or NETWORK_DISABLED)')


def get(url: str, params: Dict[str, Any] = None, timeout: float = DEFAULT_TIMEOUT, **kwargs):
    _ensure_network()
    return _SESSION.get(url, params=params, timeout=timeout, **kwargs)


def post(url: str, data: Dict[str, Any] = None, timeout: float = DEFAULT_TIMEOUT, **kwargs):
    _ensure_network()
    return _SESSION.post(url, data=data, timeout=timeout, **kwargs)
