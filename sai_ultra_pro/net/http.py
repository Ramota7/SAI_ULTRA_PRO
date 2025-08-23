"""Wrapper ligero para llamadas HTTP con timeout por defecto.

Usar import: from sai_ultra_pro.net.http import post, get
"""
from typing import Any, Dict
import requests

DEFAULT_TIMEOUT = 5

def post(url: str, data: Dict[str, Any] = None, timeout: int = DEFAULT_TIMEOUT, **kwargs):
    return requests.post(url, data=data, timeout=timeout, **kwargs)

def get(url: str, params: Dict[str, Any] = None, timeout: int = DEFAULT_TIMEOUT, **kwargs):
    return requests.get(url, params=params, timeout=timeout, **kwargs)
