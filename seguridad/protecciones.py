# Blindaje, límites, KYC, auditoría

from core.logger import Logger
from core.config import Config
import pandas as pd
from datetime import datetime
import pytz

class Protecciones:
    def __init__(self, engine=None):
        self.engine = engine
        self.logger = Logger()
        self.config = Config()

    def log_proteccion(self, msg):
        self.logger.log(f"[PROTECCIÓN] {msg}")

    def fuera_horario(self):
        ahora = datetime.now(pytz.timezone('UTC')).hour
        return not (7 <= ahora <= 20)

    def drawdown_excedido(self):
        try:
            df_ops = pd.read_csv('sai_ultra_pro/ia/ops_real.csv')
            capitales = df_ops['capital'].dropna().values
            if len(capitales) > 1:
                max_capital = max(capitales)
                min_capital = min(capitales)
                drawdown = (max_capital - min_capital) / max_capital if max_capital > 0 else 0
                self.logger.log(f"[DEBUG] Drawdown calculado: {drawdown:.3f} (max={max_capital}, min={min_capital})")
                return drawdown > 0.1
        except Exception as e:
            self.logger.error(f"[DEBUG] Error al calcular drawdown: {e}")
        return False

    def capital_protegido_insuficiente(self, capital_total):
        capital_protegido = capital_total * 0.2
        capital_riesgo = capital_total - capital_protegido
        return capital_riesgo < 50

    def racha_perdidas_superada(self):
        try:
            df_ops = pd.read_csv('sai_ultra_pro/ia/ops_real.csv')
            ultimos = df_ops.tail(30)
            resultados = list(ultimos['resultado'].astype(str))
            mejor_umbral = 3
            mejor_pf = -1
            for umbral in range(2, 7):
                pf = self._simular_profit_factor(resultados, umbral)
                if pf > mejor_pf:
                    mejor_pf = pf
                    mejor_umbral = umbral
            # Guardar el umbral óptimo en config.json, backup y registro histórico
            self._guardar_umbral_racha_config(mejor_umbral, mejor_pf)
            # Enviar alerta Telegram de autoajuste de umbral
            try:
                from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta
                mensaje = f"🧠 Autoajuste de umbral de racha de pérdidas\nNuevo valor: {mejor_umbral}\nProfit factor: {mejor_pf:.2f}"
                enviar_alerta(mensaje)
            except Exception as e:
                self.logger.error(f"[TELEGRAM] Error al enviar alerta de autoajuste: {e}")
            # Usar el umbral óptimo para la protección
            max_racha = 0
            racha_actual = 0
            log_detalle = []
            for res in resultados:
                log_detalle.append(res)
                if res.strip().lower() == 'loss':
                    racha_actual += 1
                    if racha_actual > max_racha:
                        max_racha = racha_actual
                else:
                    racha_actual = 0
            if max_racha >= mejor_umbral:
                try:
                    from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta
                    mensaje = f"⛔ Protección de racha de pérdidas activada\nRacha detectada: {max_racha}\nUmbral actual: {mejor_umbral}"
                    enviar_alerta(mensaje)
                except Exception as e:
                    self.logger.error(f"[TELEGRAM] Error al enviar alerta de protección: {e}")
            self.logger.log(f"[DEBUG] Últimos resultados para racha: {resultados}")
            self.logger.log(f"[DEBUG] Mayor racha de pérdidas detectada: {max_racha} (detalle: {log_detalle}) | Umbral óptimo PF: {mejor_umbral} (PF={mejor_pf:.2f})")
            return max_racha >= mejor_umbral
        except Exception as e:
            self.logger.error(f"[DEBUG] Error al calcular racha de pérdidas: {e}")
            return False

    def _guardar_umbral_racha_config(self, valor, pf=None):
        try:
            import json, shutil, os, csv
            from datetime import datetime
            # Backup config.json antes de modificar
            backup_dir = os.path.abspath(os.path.join(os.path.dirname(self.config.path), '../../backups'))
            os.makedirs(backup_dir, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(backup_dir, f'config_{ts}.json')
            shutil.copy2(self.config.path, backup_path)
            # Modificar config.json
            with open(self.config.path, 'r') as f:
                data = json.load(f)
            data['umbral_racha_perdidas'] = valor
            with open(self.config.path, 'w') as f:
                json.dump(data, f, indent=2)
            # Registrar histórico de umbrales
            hist_path = os.path.join(backup_dir, 'umbral_racha_historico.csv')
            existe = os.path.exists(hist_path)
            with open(hist_path, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                if not existe:
                    writer.writerow(['timestamp','umbral','profit_factor'])
                writer.writerow([ts, valor, pf if pf is not None else ''])
            # Hook para alerta Telegram si el PF mejora (implementación real pendiente)
            # self._alerta_telegram_umbral(valor, pf)
        except Exception as e:
            self.logger.error(f"[DEBUG] Error al guardar umbral_racha_perdidas en config.json o histórico: {e}")

    def _simular_profit_factor(self, resultados, umbral):
        # Simula el profit factor si se hubiera bloqueado el sistema al alcanzar el umbral de racha de pérdidas
        ganancia = 0
        perdida = 0
        racha = 0
        for res in resultados:
            if res.strip().lower() == 'loss':
                racha += 1
                if racha >= umbral:
                    break  # Se bloquea el sistema
                perdida += 1
            else:
                racha = 0
                ganancia += 1
        if perdida == 0:
            return float('inf') if ganancia > 0 else 0
        return ganancia / perdida

    def margen_libre_insuficiente(self, saldo_spot, saldo_futuros):
        return saldo_futuros < 50 and saldo_spot < 50

    def modo_simulacion_activar(self, capital_total):
        return capital_total < 50

    def calcular_riesgo_blindado(self, fase, capital, score_ia, volatilidad, drawdown, racha_perdidas, modo_recuperacion, modo_escalado):
        base = min(0.01 + 0.002*fase, 0.03)
        factor_score = 1 + max(0, score_ia - 0.7)
        factor_vol = 1 + min(max(volatilidad - 1, 0), 0.5)
        factor_drawdown = 0.5 if modo_recuperacion else (1 - min(drawdown, 0.07))
        factor_racha = 0.7 if modo_recuperacion else (1.2 if modo_escalado else 1)
        return max(0.003, base * factor_score * factor_vol * factor_drawdown * factor_racha) * capital

    def calcular_stop_loss(self, simbolo, precio_entrada):
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return round(precio_entrada * 0.995, 2)
        return round(precio_entrada * 0.99, 2)

    def calcular_trailing_stop(self, simbolo, precio_entrada):
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return round(precio_entrada * 0.995, 2)
        return round(precio_entrada * 0.99, 2)

    def calcular_lote_max(self, margen_libre, precio, apalancamiento, simbolo):
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return max(0.01, round((margen_libre * 0.5 * apalancamiento) / precio, 2))
        return max(0.01, round((margen_libre * 0.5 * apalancamiento) / precio, 3))

    def horario_permitido(self):
        ahora = datetime.now(pytz.timezone('UTC')).hour
        return 7 <= ahora <= 20

    def volatilidad_permitida(self, simbolo):
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return False
        return True

    def verificar(self, capital_total=None, saldo_spot=None, saldo_futuros=None, sim_forzada=False):
        # 1. Horario permitido
        if self.fuera_horario() and not sim_forzada:
            self.log_proteccion("Fuera de horario permitido. No se opera.")
            return False
        # 2. Drawdown
        if self.drawdown_excedido():
            self.log_proteccion("Drawdown diario/semanal excedido. Bloqueando operaciones.")
            return False
        # 3. Capital protegido insuficiente
        if capital_total is not None and self.capital_protegido_insuficiente(capital_total):
            self.log_proteccion("Solo capital protegido disponible. No se opera.")
            return False
        # 4. Racha de pérdidas
        if self.racha_perdidas_superada():
            self.log_proteccion("3 pérdidas seguidas. Bloqueando operaciones y revisando estrategia.")
            return False
        # 5. Margen libre insuficiente
        if saldo_spot is not None and saldo_futuros is not None and self.margen_libre_insuficiente(saldo_spot, saldo_futuros):
            self.log_proteccion("Margen libre insuficiente en Binance. No se abrirán operaciones.")
            return False
        # 6. Modo simulación automático
        if capital_total is not None and self.modo_simulacion_activar(capital_total):
            self.log_proteccion("Capital total menor a $50. Activando modo simulación y bloqueando operaciones reales.")
            return False
        return True
