import requests
import numpy as np

def obtener_top_activos_por_volumen(top_n=10):
    """
    Obtiene los top N activos con mayor volumen en Binance (spot).
    """
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        r = requests.get(url, timeout=10)
        data = r.json()
        usdt_pairs = [d for d in data if d['symbol'].endswith('USDT')]
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        return usdt_pairs[:top_n]
    except Exception as e:
        print(f"[seleccion_activo] Error obteniendo volumen: {e}")
        return []

def evaluar_activo(activo, tendencia_func, ia_func, spread_max=0.0015):
    """
    Evalúa un activo según tendencia, volumen, señal IA y spread.
    Retorna score y motivos.
    """
    symbol = activo['symbol']
    score = 0
    motivos = []
    # Tendencia (ejemplo: usa precios de 1h)
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
        r = requests.get(url, timeout=5)
        klines = r.json()
        closes = np.array([float(k[4]) for k in klines])
        if closes[-1] > closes[0]:
            score += 1
            motivos.append("Tendencia alcista")
        elif closes[-1] < closes[0]:
            score += 0.5
            motivos.append("Tendencia bajista")
        else:
            motivos.append("Tendencia lateral")
    except Exception as e:
        motivos.append(f"Error tendencia: {e}")

    # Volumen (relativo al top 10)
    try:
        vol = float(activo['quoteVolume'])
        score += min(vol / 1e8, 1)
        motivos.append(f"Volumen: {vol:.0f}")
    except Exception as e:
        motivos.append(f"Error volumen: {e}")

    # Señal IA (función externa, debe retornar bool o score)
    try:
        ia_score = ia_func(symbol)
        if ia_score:
            score += 1
            motivos.append("Señal IA positiva")
        else:
            motivos.append("Sin señal IA")
    except Exception as e:
        motivos.append(f"Error IA: {e}")

    # Spread (diferencia ask-bid)
    try:
        url = f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={symbol}"
        r = requests.get(url, timeout=3)
        book = r.json()
        ask = float(book['askPrice'])
        bid = float(book['bidPrice'])
        spread = (ask - bid) / ask if ask > 0 else 1
        if spread < spread_max:
            score += 1
            motivos.append(f"Spread bajo: {spread:.5f}")
        else:
            motivos.append(f"Spread alto: {spread:.5f}")
    except Exception as e:
        motivos.append(f"Error spread: {e}")

    return score, motivos

def seleccionar_activo_favorable(tendencia_func, ia_func):
    """
    Evalúa los 10 activos con mayor volumen y retorna el más favorable.
    """
    top_activos = obtener_top_activos_por_volumen(10)
    mejor_score = -1
    mejor_activo = None
    mejor_motivos = []
    for activo in top_activos:
        score, motivos = evaluar_activo(activo, tendencia_func, ia_func)
        if score > mejor_score:
            mejor_score = score
            mejor_activo = activo
            mejor_motivos = motivos
    return mejor_activo, mejor_score, mejor_motivos

"""
Módulo: seleccion_activo.py
Propósito: Proporciona utilidades y lógica para la selección dinámica de activos financieros a analizar o operar.

Este módulo puede incluir funciones para:
- Selección dinámica de archivos de datos según criterios configurables.
- Gestión de configuración para la selección de activos.
- Registro (logs) de las decisiones de selección.
- Integración con otros módulos de estrategias o análisis.
"""
