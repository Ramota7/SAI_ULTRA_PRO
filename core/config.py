# Configuración centralizada y gestión de credenciales
import json
class Config:
    def __init__(self, path='sai_ultra_pro/config/config.json'):
        self.path = path
        self.data = self.cargar()
    def cargar(self):
        try:
            with open(self.path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
