"""Stub package for tensorflow.keras that forwards to the minimal keras
namespace defined in the parent `tensorflow` stub.
"""

from .. import keras as _keras

# Expose `models` and `layers` as attributes on tensorflow.keras
models = _keras.models
layers = _keras.layers
