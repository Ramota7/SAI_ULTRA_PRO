"""Minimal stub for tensorflow used in CI tests.

This stub provides a very small subset of the real tensorflow API used by the
code under test: a `keras` package with `models.load_model` and a fake
`Sequential` class. It's intentionally tiny and suitable only for unit tests
that don't need real ML execution.
"""

from types import SimpleNamespace


def _load_model(path=None, compile=True):
    class DummyModel:
        def predict(self, *args, **kwargs):
            return None

        def save(self, *args, **kwargs):
            return None

    return DummyModel()


class Sequential:
    def __init__(self, *args, **kwargs):
        self.layers = []

    def add(self, layer):
        self.layers.append(layer)

    def compile(self, *args, **kwargs):
        return None

    def fit(self, *args, **kwargs):
        return SimpleNamespace(history={})


# Build a minimal keras namespace with models and layers submodules used by code
keras = SimpleNamespace(models=SimpleNamespace(load_model=_load_model), layers=SimpleNamespace())
