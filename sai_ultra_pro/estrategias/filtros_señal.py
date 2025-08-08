import numpy as np
import pandas as pd

def filtro_calidad_señal(series_precio, umbral_rsi=50, ventana=14):
    """
    Filtra señales basadas en la calidad, usando RSI y consistencia de tendencia.
    Args:
        series_precio (pd.Series): Serie de precios.
        umbral_rsi (float): Umbral mínimo de RSI para considerar la señal de calidad.
        ventana (int): Ventana para el cálculo del RSI.
    Returns:
        bool: True si la señal es de calidad, False si no.
    """
    delta = series_precio.diff()
    ganancia = delta.clip(lower=0)
    perdida = -delta.clip(upper=0)
    media_ganancia = ganancia.rolling(window=ventana).mean()
    media_perdida = perdida.rolling(window=ventana).mean()
    rs = media_ganancia / (media_perdida + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    rsi_actual = rsi.iloc[-1]
    tendencia = series_precio.iloc[-ventana:].mean() > series_precio.iloc[-2*ventana:-ventana].mean()
    return rsi_actual > umbral_rsi and tendencia

def filtro_momentum(series_precio, ventana_corta=10, ventana_larga=30):
    """
    Filtra señales basadas en momentum usando cruce de medias móviles.
    Args:
        series_precio (pd.Series): Serie de precios.
        ventana_corta (int): Ventana para la media móvil corta.
        ventana_larga (int): Ventana para la media móvil larga.
    Returns:
        bool: True si hay momentum positivo, False si no.
    """
    ma_corta = series_precio.rolling(window=ventana_corta).mean()
    ma_larga = series_precio.rolling(window=ventana_larga).mean()
    cruce = ma_corta.iloc[-1] > ma_larga.iloc[-1] and ma_corta.iloc[-2] <= ma_larga.iloc[-2]
    return cruce

def filtro_volatilidad(series_precio, ventana=14, umbral_vol=0.01):
    """
    Filtra señales según volatilidad usando ATR (Average True Range).
    Args:
        series_precio (pd.Series): Serie de precios.
        ventana (int): Ventana para el cálculo del ATR.
        umbral_vol (float): Umbral mínimo de volatilidad relativa.
    Returns:
        bool: True si la volatilidad es suficiente, False si no.
    """
    precios = series_precio.values
    tr = np.maximum.reduce([
        precios[1:] - precios[:-1],
        np.abs(precios[1:] - precios[:-1]),
        np.abs(precios[1:] - precios[:-1])
    ])
    atr = pd.Series(tr).rolling(window=ventana).mean().iloc[-1]
    volatilidad_relativa = atr / series_precio.iloc[-ventana:].mean()
    return volatilidad_relativa > umbral_vol

def aplicar_filtros(series_precio, config=None):
    """
    Aplica todos los filtros avanzados y retorna un dict con los resultados.
    Args:
        series_precio (pd.Series): Serie de precios.
        config (dict): Configuración de umbrales y ventanas para los filtros.
    Returns:
        dict: Resultados de cada filtro.
    """
    if config is None:
        config = {}
    return {
        'calidad': filtro_calidad_señal(series_precio,
                                        umbral_rsi=config.get('umbral_rsi', 50),
                                        ventana=config.get('ventana_rsi', 14)),
        'momentum': filtro_momentum(series_precio,
                                    ventana_corta=config.get('ventana_corta', 10),
                                    ventana_larga=config.get('ventana_larga', 30)),
        'volatilidad': filtro_volatilidad(series_precio,
                                         ventana=config.get('ventana_vol', 14),
                                         umbral_vol=config.get('umbral_vol', 0.01))
    }

# Ejemplo de uso:
# import pandas as pd
# precios = pd.Series([...])
# resultado = aplicar_filtros(precios)
