# Interfaz base para estrategias
# Estrategia base abstracta
class EstrategiaBase:
    nombre = "base"
    def evaluar(self, datos, noticias=None, sentimiento=None):
        raise NotImplementedError("Debes implementar evaluar() en la subclase")

# Estrategia Momentum real de ejemplo
class EstrategiaMomentum(EstrategiaBase):
    nombre = "momentum"
    def __init__(self, umbral=0.01, ventana=10):
        self.umbral = umbral
        self.ventana = ventana

    def evaluar(self, datos, noticias=None, sentimiento=None):
        precios = datos.get("precios", [])
        if len(precios) < self.ventana:
            return None
        cambio = (precios[-1] - precios[-self.ventana]) / precios[-self.ventana]
        if cambio > self.umbral:
            return {"tipo": "compra", "fuerza": cambio, "estrategia": self.nombre}
        elif cambio < -self.umbral:
            return {"tipo": "venta", "fuerza": cambio, "estrategia": self.nombre}
        return None

# Estrategia avanzada: Arbitraje Estadístico
import numpy as np
class EstrategiaArbitrajeEstadistico(EstrategiaBase):
    nombre = "arbitraje_estadistico"
    def __init__(self, umbral_z=2.0, ventana=30):
        self.umbral_z = umbral_z
        self.ventana = ventana

    def evaluar(self, datos, noticias=None, sentimiento=None):
        precios_a = datos.get("precios_a", [])
        precios_b = datos.get("precios_b", [])
        if len(precios_a) < self.ventana or len(precios_b) < self.ventana:
            return None
        spread = np.array(precios_a[-self.ventana:]) - np.array(precios_b[-self.ventana:])
        media = np.mean(spread)
        std = np.std(spread)
        z = (spread[-1] - media) / std if std > 0 else 0
        if z > self.umbral_z:
            return {"tipo": "venta_a_compra_b", "z": z, "estrategia": self.nombre}
        elif z < -self.umbral_z:
            return {"tipo": "compra_a_venta_b", "z": z, "estrategia": self.nombre}
        return None
