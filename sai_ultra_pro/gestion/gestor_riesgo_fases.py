
import json
from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta

class GestorRiesgoFases:
    def __init__(self, fase_actual, capital, porcentaje_riesgo):
        self.config = self.cargar_config()
        self.fases = self.config.get('fases', [
            {"min": 226, "max": 500, "riesgo": 0.01, "estrategias": ["ICT", "Ballena"]},
            {"min": 500, "max": 1500, "riesgo": 0.02, "estrategias": ["ICT", "Ballena", "Arbitraje"]},
            {"min": 1500, "max": 5000, "riesgo": 0.03, "estrategias": ["ICT", "Ballena"], "doble_entrada": True},
            {"min": 5000, "max": 25000, "riesgo": 0.04, "estrategias": ["ICT", "Ballena", "Arbitraje"], "prioridad_ia": True},
            {"min": 25000, "max": 100000, "riesgo": 0.05, "estrategias": ["ICT", "Ballena", "Arbitraje"], "arbitraje_spread": 0.007},
            {"min": 100000, "max": 1000000, "riesgo": 0.07, "estrategias": ["ICT", "Ballena", "Arbitraje"], "ultra_validacion": True}
        ])
        self.capital = capital
        self.fase_idx = self.detectar_fase(capital)
        self.fase_actual = self.fase_idx + 1
        self.porcentaje_riesgo = self.fases[self.fase_idx]["riesgo"]
        self.estrategias_activas = self.fases[self.fase_idx]["estrategias"]
        self.doble_entrada = self.fases[self.fase_idx].get("doble_entrada", False)
        self.prioridad_ia = self.fases[self.fase_idx].get("prioridad_ia", False)
        self.arbitraje_spread = self.fases[self.fase_idx].get("arbitraje_spread", 0.003)
        self.ultra_validacion = self.fases[self.fase_idx].get("ultra_validacion", False)
        self.fase_anterior = fase_actual
        if self.fase_actual != self.fase_anterior:
            self.notificar_cambio_fase()

    def cargar_config(self):
        try:
            with open('sai_ultra_pro/config/config.json') as f:
                return json.load(f)
        except:
            return {}

    def detectar_fase(self, capital):
        for idx, fase in enumerate(self.fases):
            if fase["min"] <= capital < fase["max"]:
                return idx
        if capital >= self.fases[-1]["max"]:
            return len(self.fases)-1
        return 0

    def calcular_tamano_operacion(self):
        # Tamaño = saldo * % riesgo
        return round(self.capital * self.porcentaje_riesgo, 2)

    def actualizar_capital(self, nuevo_capital):
        nueva_fase = self.detectar_fase(nuevo_capital) + 1
        if nueva_fase < self.fase_actual:
            self.modo_proteccion()
        if nueva_fase != self.fase_actual:
            self.fase_actual = nueva_fase
            self.fase_idx = nueva_fase - 1
            self.porcentaje_riesgo = self.fases[self.fase_idx]["riesgo"]
            self.estrategias_activas = self.fases[self.fase_idx]["estrategias"]
            self.doble_entrada = self.fases[self.fase_idx].get("doble_entrada", False)
            self.prioridad_ia = self.fases[self.fase_idx].get("prioridad_ia", False)
            self.arbitraje_spread = self.fases[self.fase_idx].get("arbitraje_spread", 0.003)
            self.ultra_validacion = self.fases[self.fase_idx].get("ultra_validacion", False)
            self.notificar_cambio_fase()
        self.capital = nuevo_capital

    def notificar_cambio_fase(self):
        msg = f"Cambio de fase: ahora en Fase {self.fase_actual} | Capital: ${self.capital} | Riesgo: {int(self.porcentaje_riesgo*100)}% | Estrategias: {', '.join(self.estrategias_activas)}"
        enviar_alerta(msg)

    def modo_proteccion(self):
        enviar_alerta(f"Capital bajo el mínimo de la fase. Bot en modo protección. No se operará hasta recuperar nivel.")
