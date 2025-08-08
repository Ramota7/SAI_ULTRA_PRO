import numpy as np

class SalidasAvanzadas:
    def __init__(self, entrada, stop, target, tipo='long'):
        self.entrada = entrada
        self.stop = stop
        self.target = target
        self.tipo = tipo
        self.r = abs(entrada - stop)
        self.salida_parcial = False
        self.salida_total = False
        self.trailing = stop

    def actualizar(self, precio_actual, impulso=1.0):
        """
        Actualiza el estado de la operación según el precio actual e impulso.
        - Activa trailing stop dinámico desde 1R.
        - Toma 50% de ganancia en 2R.
        - Cierra totalmente si impulso < 0.3 o se alcanza el target.
        """
        resultado = None
        # 1. Trailing stop dinámico desde 1R
        if self.tipo == 'long':
            if precio_actual >= self.entrada + self.r:
                self.trailing = max(self.trailing, precio_actual - self.r)
            if precio_actual <= self.trailing:
                self.salida_total = True
                resultado = 'trailing_stop_hit'
        else:
            if precio_actual <= self.entrada - self.r:
                self.trailing = min(self.trailing, precio_actual + self.r)
            if precio_actual >= self.trailing:
                self.salida_total = True
                resultado = 'trailing_stop_hit'

        # 2. Toma parcial en 2R
        if not self.salida_parcial:
            if self.tipo == 'long' and precio_actual >= self.entrada + 2*self.r:
                self.salida_parcial = True
                resultado = 'take_profit_2R_50pct'
            elif self.tipo == 'short' and precio_actual <= self.entrada - 2*self.r:
                self.salida_parcial = True
                resultado = 'take_profit_2R_50pct'

        # 3. Cierre total por impulso bajo o target
        if impulso < 0.3:
            self.salida_total = True
            resultado = 'impulso_agotado'
        if (self.tipo == 'long' and precio_actual >= self.target) or (self.tipo == 'short' and precio_actual <= self.target):
            self.salida_total = True
            resultado = 'target_hit'

        return resultado
