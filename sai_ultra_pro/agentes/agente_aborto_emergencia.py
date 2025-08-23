import os
import pandas as pd
from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta

class AgenteAbortoEmergencia:
    """
    Agente robusto para abortar operaciones y detener el sistema ante condiciones críticas:
    - Drawdown extremo
    - Racha de SL consecutivos
    - Pérdida de conexión API
    - Señales IA anómalas
    - Volatilidad extrema
    """
    def __init__(self, config_path='sai_ultra_pro/config/config.json', ops_path='sai_ultra_pro/ia/ops_real.csv'):
        self.config_path = config_path
        self.ops_path = ops_path
        self.umbrales = {
            'drawdown': 0.25,
            'racha_sl': 5,
            'volatilidad': 0.04,
            'api_fallos': 3,
            'ia_anomalia': 0.2
        }
        self.api_fallos = 0

    def chequear_drawdown(self):
        if not os.path.exists(self.ops_path):
            return False, 0
        df = pd.read_csv(self.ops_path)
        if df.empty or 'capital' not in df.columns:
            return False, 0
        max_cap = df['capital'].astype(float).cummax()
        dd = (max_cap - df['capital'].astype(float)) / max_cap
        drawdown = dd.max() if not dd.empty else 0
        return drawdown > self.umbrales['drawdown'], drawdown

    def chequear_racha_sl(self):
        if not os.path.exists(self.ops_path):
            return False, 0
        df = pd.read_csv(self.ops_path)
        if df.empty or 'resultado' not in df.columns:
            return False, 0
        racha = 0
        for res in df['resultado'][::-1]:
            if res == 'SL':
                racha += 1
            else:
                break
        return racha >= self.umbrales['racha_sl'], racha

    def chequear_volatilidad(self, data_path):
        if not os.path.exists(data_path):
            return False, 0
        df = pd.read_csv(data_path)
        if df.empty or 'close' not in df.columns:
            return False, 0
        vol = df['close'].pct_change().tail(50).std()
        return vol > self.umbrales['volatilidad'], vol

    def chequear_api(self, api_status):
        if not api_status:
            self.api_fallos += 1
        else:
            self.api_fallos = 0
        return self.api_fallos >= self.umbrales['api_fallos'], self.api_fallos

    def chequear_ia(self, score_ia):
        return score_ia < self.umbrales['ia_anomalia'], score_ia

    def abortar(self, motivo, detalle):
        msg = f"[ABORTO EMERGENCIA] Motivo: {motivo}\nDetalle: {detalle}\nOperaciones detenidas y sistema en pausa."
        print(msg)
        enviar_alerta(msg)
        # Aquí puedes agregar lógica para pausar el ciclo principal, cerrar posiciones, etc.
        # Por ejemplo, crear un archivo de lock o cambiar un flag global
        with open('sai_ultra_pro/lockdown.flag', 'w') as f:
            f.write(f"ABORTADO: {motivo} | {detalle}")

    def monitorear(self, data_path, api_status, score_ia):
        # Chequeos críticos
        dd_flag, dd = self.chequear_drawdown()
        racha_flag, racha = self.chequear_racha_sl()
        vol_flag, vol = self.chequear_volatilidad(data_path)
        api_flag, api_fallos = self.chequear_api(api_status)
        ia_flag, ia_score = self.chequear_ia(score_ia)
        if dd_flag:
            self.abortar('Drawdown extremo', f'Drawdown: {dd:.2%}')
            return True
        if racha_flag:
            self.abortar('Racha de SL consecutivos', f'Racha: {racha}')
            return True
        if vol_flag:
            self.abortar('Volatilidad extrema', f'Volatilidad: {vol:.2%}')
            return True
        if api_flag:
            self.abortar('Fallas de conexión API', f'Fallos consecutivos: {api_fallos}')
            return True
        if ia_flag:
            self.abortar('Señales IA anómalas', f'Score IA: {ia_score:.2f}')
            return True
        return False