"""Minimal `models` stub exposing `load_model` used by the code under test."""

def load_model(path=None, compile=True):
    class DummyModel:
        def predict(self, *args, **kwargs):
            return None

        def save(self, *args, **kwargs):
            return None

    return DummyModel()
