import os
import pytest
import faulthandler
import sys

# Fixture autouse que bloquea acceso a red para tests salvo si SAI_ALLOW_NET == '1'
@pytest.fixture(autouse=True)
def _block_network(monkeypatch):
    allow = os.environ.get('SAI_ALLOW_NET', '') == '1'
    if allow:
        return

    def _raise(*args, **kwargs):
        raise RuntimeError('Network access disabled by tests (SAI_ALLOW_NET!=1)')

    try:
        import requests
        monkeypatch.setattr(requests, 'get', _raise)
        monkeypatch.setattr(requests, 'post', _raise)
        # Sessions
        if hasattr(requests, 'Session'):
            class DummySession:
                def __init__(self, *a, **k):
                    pass
                def get(self, *a, **k):
                    return _raise()
                def post(self, *a, **k):
                    return _raise()
            monkeypatch.setattr(requests, 'Session', DummySession)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _faulthandler_timeout():
    # Si el test cuelga, volcar traza tras 45s
    faulthandler.dump_traceback_later(45, file=sys.stderr)
    yield
    faulthandler.cancel_dump_traceback_later()

