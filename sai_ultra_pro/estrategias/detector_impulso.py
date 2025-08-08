import numpy as np

def detectar_impulso(df):
    """
    Analiza velas recientes y detecta impulsos fuertes.
    df: DataFrame con columnas ['open', 'high', 'low', 'close', 'volume']
    Retorna True si la última vela es un impulso fuerte según:
      - Cuerpo >= 60% del rango total
      - Volumen > promedio últimas 20 velas
      - Cierre > cierre anterior (aceleración alcista) o cierre < cierre anterior (bajista)
    """
    if df is None or len(df) < 21:
        return False
    vela = df.iloc[-1]
    vela_ant = df.iloc[-2]
    cuerpo = abs(vela['close'] - vela['open'])
    rango = vela['high'] - vela['low']
    if rango == 0:
        return False
    prop_cuerpo = cuerpo / rango
    volumen_prom = df['volume'].iloc[-21:-1].mean()
    volumen_actual = vela['volume']
    aceleracion = (vela['close'] > vela_ant['close']) or (vela['close'] < vela_ant['close'])
    if (
        prop_cuerpo >= 0.6
        and volumen_actual > volumen_prom
        and aceleracion
    ):
        return True
    return False