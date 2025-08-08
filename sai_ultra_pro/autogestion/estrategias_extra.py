"""
Estrategias adicionales y utilidades para el sistema de trading unicornio.
Incluye momentum, reversión, breakout, arbitraje estadístico y lógica de rotación avanzada.
"""
import numpy as np
import pandas as pd

def estrategia_momentum(df):
    """Ejemplo: compra si la media móvil corta supera a la larga."""
    df['ma_corta'] = df['close'].rolling(5).mean()
    df['ma_larga'] = df['close'].rolling(20).mean()
    return (df['ma_corta'].iloc[-1] > df['ma_larga'].iloc[-1])

def estrategia_reversion(df):
    """Ejemplo: compra si el precio cae mucho respecto a la media."""
    media = df['close'].rolling(20).mean().iloc[-1]
    return (df['close'].iloc[-1] < media * 0.97)

def estrategia_breakout(df):
    """Ejemplo: compra si el precio rompe el máximo de 20 velas."""
    return (df['close'].iloc[-1] > df['high'].rolling(20).max().iloc[-2])

def estrategia_arbitraje_estadistico(df1, df2):
    """Ejemplo: arbitraje entre dos activos correlacionados."""
    spread = df1['close'] - df2['close']
    zscore = (spread - spread.mean()) / spread.std()
    return (zscore.iloc[-1] > 2) or (zscore.iloc[-1] < -2)

def priorizar_por_liquidez_y_volumen(lista_activos, info_mercado):
    """Ordena activos priorizando mayor volumen y menor spread."""
    return sorted(lista_activos, key=lambda x: (-info_mercado[x]['volumen'], info_mercado[x]['spread']))

def rotacion_activos_rendimiento(historial):
    """Rota activos priorizando los de mejor rendimiento reciente."""
    ranking = historial.groupby('activo')['resultado'].mean().sort_values(ascending=False)
    return list(ranking.index)

def alerta_oportunidad(volatilidad, correlacion):
    """Genera alerta si hay volatilidad extrema o baja correlación."""
    if volatilidad > 2:
        return "[ALERTA] Volatilidad extrema: oportunidad de breakout o arbitraje."
    if correlacion < 0.2:
        return "[ALERTA] Correlación baja: oportunidad de diversificación."
    return None
