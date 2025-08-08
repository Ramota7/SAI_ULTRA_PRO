import os
import csv

class GestionRacha:
    def __init__(self, path_ops='sai_ultra_pro/ia/ops_real.csv', riesgo_base=0.01):
        self.path_ops = path_ops
        self.riesgo_base = riesgo_base
        self.riesgo_actual = riesgo_base
        self.racha = 0
        self.tipo_racha = None  # 'ganadora', 'perdedora', None
        self._calcular_racha()

    def _calcular_racha(self):
        if not os.path.exists(self.path_ops):
            self.racha = 0
            self.tipo_racha = None
            self.riesgo_actual = self.riesgo_base
            return
        with open(self.path_ops, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        if len(rows) < 2:
            self.racha = 0
            self.tipo_racha = None
            self.riesgo_actual = self.riesgo_base
            return
        resultados = [row[2] for row in rows[1:] if len(row) > 2]
        racha = 0
        tipo = None
        for res in reversed(resultados):
            if res == 'TP':
                if racha < 0:
                    break
                racha += 1
                tipo = 'ganadora'
            elif res == 'SL':
                if racha > 0:
                    break
                racha -= 1
                tipo = 'perdedora'
            else:
                break
        self.racha = abs(racha)
        self.tipo_racha = tipo
        # Ajuste de riesgo
        if tipo == 'perdedora' and self.racha >= 2:
            self.riesgo_actual = self.riesgo_base / 2
        elif tipo == 'ganadora' and self.racha >= 3:
            self.riesgo_actual = self.riesgo_base * 1.25
        else:
            self.riesgo_actual = self.riesgo_base

    def get_riesgo(self):
        self._calcular_racha()
        return self.riesgo_actual
