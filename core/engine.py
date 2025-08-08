# Motor principal del bot unicornio

from core.logger import Logger
from core.config import Config
from estrategias.estrategia_base import EstrategiaBase, EstrategiaMomentum, EstrategiaArbitrajeEstadistico
from ml.entrenador import Entrenador
from ml.refuerzo import Refuerzo
from ml.simulador import Simulador
from brokers.binance_adapter import BinanceAdapter
from brokers.exness_adapter import ExnessAdapter
from data.historicos import Historicos
from data.noticias import Noticias
from data.sentimiento import Sentimiento
from api.rest import RestAPI
from api.websocket import WebSocketAPI
from ui.dashboard import Dashboard
from automejora.federated import FederatedLearning
from automejora.torneo import TorneoEstrategias
from seguridad.protecciones import Protecciones
from seguridad.watchdog import Watchdog
from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta
import numpy as np


class Engine:
    def validar_protecciones(self):
        self.logger.log("[VALIDACIÓN] Iniciando ciclo de validación automática de protecciones...")
        try:
            enviar_alerta("✅ Bot iniciado correctamente (validación de protecciones)")
        except Exception:
            pass
        # 1. Capital bajo
        ok = self.protecciones.verificar(capital_total=10, saldo_spot=100, saldo_futuros=100, sim_forzada=False)
        if not ok:
            self.logger.log("[VALIDACIÓN] Protección de capital bajo: OK")
            try:
                enviar_alerta("🔒 Capital protegido activado: solo capital protegido disponible, operaciones pausadas.")
            except Exception:
                pass
        else:
            self.logger.error("[VALIDACIÓN] FALLO: No se bloqueó por capital bajo")
        # 2. Drawdown alto (simular con log)
        ok = self.protecciones.drawdown_excedido()
        if ok:
            self.logger.log("[VALIDACIÓN] Protección de drawdown: OK")
            try:
                enviar_alerta("📉 Drawdown alto detectado: reducción de riesgo o pausa operativa.")
            except Exception:
                pass
        else:
            self.logger.error("[VALIDACIÓN] FALLO: No se bloqueó por drawdown")
        # 3. Fuera de horario
        ok = self.protecciones.verificar(capital_total=10000, saldo_spot=100, saldo_futuros=100, sim_forzada=False)
        if not ok:
            self.logger.log("[VALIDACIÓN] Protección de horario: OK")
            try:
                enviar_alerta("🕐 Restricción por horario activada: fuera del rango permitido.")
            except Exception:
                pass
        else:
            self.logger.error("[VALIDACIÓN] FALLO: No se bloqueó fuera de horario")
        # 4. Racha de pérdidas (simulada)
        ok = self.protecciones.racha_perdidas_superada()
        if ok:
            self.logger.log("[VALIDACIÓN] Protección de racha de pérdidas: OK")
        else:
            self.logger.error("[VALIDACIÓN] FALLO: No se bloqueó por racha de pérdidas")
        self.logger.log("[VALIDACIÓN] Ciclo de validación automática finalizado.")
    def __init__(self):
        self.logger = Logger()
        self.config = Config()
        # Múltiples estrategias avanzadas
        self.estrategias = [
            EstrategiaMomentum(umbral=0.01, ventana=10),
            EstrategiaArbitrajeEstadistico(umbral_z=2.0, ventana=30)
        ]
        self.entrenador = Entrenador()
        self.refuerzo = Refuerzo()
        self.simulador = Simulador()
        self.brokers = {
            'binance': BinanceAdapter(),
            'exness': ExnessAdapter()
        }
        self.historicos = Historicos()
        self.noticias = Noticias()
        self.sentimiento = Sentimiento()
        self.api_rest = RestAPI(self)
        self.api_ws = WebSocketAPI(self)
        self.dashboard = Dashboard(self)
        self.federated = FederatedLearning(self)
        self.torneo = TorneoEstrategias(self)
        self.protecciones = Protecciones(self)
        self.watchdog = Watchdog(self)
        # Estado de portafolio
        self.capital_total = 10000  # Simulado, reemplazar por consulta real
        self.riesgo_max = 0.02  # 2% por operación
        self.asignacion = {e.nombre: 1/len(self.estrategias) for e in self.estrategias}
        # Métricas simuladas por estrategia
        self.performance = {e.nombre: {"sharpe": 1.0, "winrate": 0.6, "drawdown": 0.05, "racha": 0} for e in self.estrategias}
        self.volatilidad = 0.02  # Simulada

    def run(self, validar=False):
        self.modo_simulacion = True  # Forzar modo simulación para prueba de alertas
        self.logger.log("[UNICORNIO] Motor iniciado.")
        try:
            enviar_alerta("✅ Bot iniciado correctamente")
        except Exception:
            pass
        self.watchdog.start()
        self.api_rest.start()
        self.api_ws.start()
        self.dashboard.start()
        self.protecciones.verificar()
        self.federated.sync()
        self.torneo.competir()
        self.entrenador.auto_reentrenar()
        self.simulador.ejecutar_backtesting()
        self.refuerzo.entrenar()
        if validar:
            self.validar_protecciones()
            return
        ciclo_num = 0
        # Ciclo principal de trading con gestión dinámica de portafolio y riesgo
        while True:
            ciclo_num += 1
            self.logger.log(f"[UNICORNIO] Nuevo ciclo de trading #{ciclo_num}.")
            try:
                enviar_alerta(f"🟢 Nuevo ciclo de trading #{ciclo_num}")
            except Exception:
                pass
            datos = self.historicos.obtener_datos()
            # Simulación de datos para arbitraje estadístico
            datos["precios_a"] = [100 + np.sin(i/10) + np.random.normal(0,0.5) for i in range(100)]
            datos["precios_b"] = [100 + np.cos(i/10) + np.random.normal(0,0.5) for i in range(100)]
            noticias = self.noticias.obtener()
            sentimiento = self.sentimiento.analizar()
            señales = []
            for estrategia in self.estrategias:
                señal = estrategia.evaluar(datos, noticias, sentimiento)
                if señal:
                    señales.append((estrategia.nombre, señal))

            # === PROTECCIONES Y GESTIÓN DE RIESGO ===
            proteccion_ok = self.protecciones.verificar(
                capital_total=self.capital_total,
                saldo_spot=100,  # Simulado, reemplazar por consulta real
                saldo_futuros=100,  # Simulado, reemplazar por consulta real
                sim_forzada=False
            )
            if not proteccion_ok:
                self.logger.log("[PORTAFOLIO] Ciclo bloqueado por protección activa.")
                try:
                    enviar_alerta("⛔ Ciclo bloqueado por protección activa.")
                except Exception:
                    pass
                continue

            # === Criterios avanzados de asignación dinámica ===
            pesos_perf = {}
            for nombre, met in self.performance.items():
                score = max(0.01, met["sharpe"] * met["winrate"] / (1 + met["drawdown"]))
                if met["racha"] < 0:
                    score *= max(0.1, 1 + met["racha"] * 0.2)
                pesos_perf[nombre] = score
            suma_pesos = sum(pesos_perf.values())
            if suma_pesos > 0:
                for k in pesos_perf:
                    pesos_perf[k] /= suma_pesos
            riesgo_vol = self.riesgo_max * max(0.5, 1 - self.volatilidad * 10)
            tipos = [s[1]["tipo"] for s in señales]
            bonificacion = 1.0
            if len(set(tipos)) == 1 and len(señales) > 1:
                bonificacion = 1.5
            correlacion = 0.8 if "momentum" in [s[0] for s in señales] and "arbitraje_estadistico" in [s[0] for s in señales] else 0.2
            limitador_corr = 1.0 - correlacion * 0.5
            resumen_operaciones = []
            rotacion = False
            estrategia_anterior = getattr(self, 'estrategia_activa', None)
            if señales:
                capital_disponible = self.capital_total * limitador_corr
                for nombre, señal in señales:
                    pct = pesos_perf.get(nombre, 1/len(self.estrategias))
                    capital_estrategia = capital_disponible * pct * riesgo_vol * bonificacion
                    self.logger.log(f"[PORTAFOLIO] Asignando ${capital_estrategia:.2f} a {nombre} por señal: {señal} (peso={pct:.2f}, riesgo_vol={riesgo_vol:.3f}, bonif={bonificacion}, corr={limitador_corr:.2f})")
                    for broker, adapter in self.brokers.items():
                        adapter.ejecutar_orden({**señal, "capital": capital_estrategia})
                        # Alerta Telegram de operación ejecutada
                        try:
                            mensaje = f"💼 Operación ejecutada\nBroker: {broker}\nEstrategia: {nombre}\nSímbolo: {señal.get('simbolo','?')}\nTipo: {señal.get('tipo','?')}\nCapital: ${capital_estrategia:.2f}"
                            enviar_alerta(mensaje)
                        except Exception:
                            pass
                        resumen_operaciones.append((broker, nombre, señal.get('simbolo','?'), señal.get('tipo','?'), capital_estrategia))
                # Rotación de estrategia (si cambia la mejor)
                mejor_estrategia = max(pesos_perf, key=pesos_perf.get)
                if estrategia_anterior != mejor_estrategia:
                    rotacion = True
                    self.estrategia_activa = mejor_estrategia
                    try:
                        enviar_alerta(f"🔁 Rotación de estrategia: ahora activa {mejor_estrategia}")
                    except Exception:
                        pass
                # Resumen de ciclo
                try:
                    mensaje = f"📊 Resumen de ciclo #{ciclo_num}:\nOperaciones: {len(resumen_operaciones)}\n" + "\n".join([f"{b} | {e} | {s} | {t} | ${c:.2f}" for b,e,s,t,c in resumen_operaciones])
                    enviar_alerta(mensaje)
                except Exception:
                    pass
            else:
                self.logger.log("[PORTAFOLIO] Sin señales válidas en este ciclo.")
                try:
                    enviar_alerta("[PORTAFOLIO] Sin señales válidas en este ciclo.")
                except Exception:
                    pass
            # Eventos de seguridad (modo simulación, API, backup, config)
            if getattr(self, 'modo_simulacion', False):
                try:
                    enviar_alerta("🧪 Modo simulación activado")
                except Exception:
                    pass
            # Aquí puedes agregar más eventos de seguridad según sea necesario
            self.protecciones.verificar()
            self.watchdog.check()
            self.federated.sync()
            self.torneo.competir()
            self.entrenador.auto_reentrenar()
            self.simulador.ejecutar_backtesting()
            self.refuerzo.entrenar()
            # Espera entre ciclos (puedes ajustar a tu necesidad)
            import time
            time.sleep(60)
