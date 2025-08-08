# Adaptador para Exness
from core.logger import Logger
class ExnessAdapter:
    def __init__(self):
        self.logger = Logger()
    def ejecutar_orden(self, señal):
        # Lógica simulada: solo loguea la orden
        self.logger.audit(f"[EXNESS] Ejecutando orden: {señal}")
        # Aquí iría la integración real con la API de Exness
        return True
