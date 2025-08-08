"""
Módulo de autogestión y adaptación automática para el ciclo principal.
Incluye rotación de estrategias, ajuste de riesgo y selección dinámica de activos.
"""
import numpy as np
import pandas as pd

def evaluar_entorno_y_rotar_estrategia(métricas, entorno):
    """
    Decide la estrategia óptima según métricas y entorno.
    Retorna el nombre de la estrategia a usar.
    """
    if métricas['winrate'] < 45 or métricas['drawdown'] > 0.15:
        return 'defensiva'
    if entorno['volatilidad'] > 1.5:
        return 'arbitraje'
    if métricas['profit_factor'] > 1.5 and métricas['winrate'] > 60:
        return 'tendencia'
    return 'mixta'

def ajustar_riesgo_y_apalancamiento(métricas, entorno):
    """
    Ajusta el tamaño de operación y apalancamiento según métricas y entorno.
    Retorna (riesgo_pct, apalancamiento).
    """
    base = 0.01
    if métricas['drawdown'] > 0.1 or métricas['racha_perdidas'] >= 2:
        return (base * 0.5, 2)
    if métricas['racha_ganadora'] >= 3:
        return (base * 1.5, 5)
    if entorno['volatilidad'] > 1.5:
        return (base * 0.7, 3)
    return (base, 3)

def seleccionar_activos_dinamicamente(métricas, historial):
    """
    Prioriza activos con mejor rendimiento y menor correlación.
    Retorna lista priorizada de símbolos.
    """
    activos = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'MATICUSDT', 'XRPUSDT', 'ADAUSDT']
    if métricas['racha_perdidas'] >= 2:
        return ['ADAUSDT', 'MATICUSDT', 'XRPUSDT', 'SOLUSDT', 'BTCUSDT', 'ETHUSDT']
    return activos
