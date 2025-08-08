# Descarga y gestión de datos históricos
import random
class Historicos:
    def obtener_datos(self):
        # Simula una serie de precios para pruebas
        precios = [100 + random.gauss(0, 1) for _ in range(100)]
        return {"precios": precios}
