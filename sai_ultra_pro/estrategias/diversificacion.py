
import numpy as np

from .ultra_rompimientos_ict import UltraRompimientosICT
from .liquidez_ballena import LiquidezBallena
from .arbitraje_oculto import ArbitrajeOculto
from .multi_timeframe import MultiTimeframeValidator
from .simulador_patron import SimuladorPatron
from gestion.liquidez_slippage import estimar_slippage_y_liquidez

PARES = [
    {'binance': 'BTCUSDT', 'exness': 'BTCUSD'},
    {'binance': 'ETHUSDT', 'exness': 'ETHUSD'},
    {'binance': 'None', 'exness': 'XAUUSDm'}
]
ESTRATEGIAS = ['ICT', 'Ballena', 'Arbitraje']

def evaluar_estrategias_y_activos(gestor, capital_total):
    """
    Evalúa todas las combinaciones de pares y estrategias, retorna señales válidas y su score de calidad.
    """
    resultados = []
    for par in PARES:
        # ICT
        ict = UltraRompimientosICT()
        ict.symbol = par['binance']
        if ict.ia_confirmacion():
            s = ict.señal
            base_tf = s.get('timeframe', '15m') if s else '15m'
            tipo = s.get('tipo', 'compra') if s else 'compra'
            mtf = MultiTimeframeValidator(par['binance'], base_tf)
            def patron_func_ict(df):
                # ...lógica realista...
                if len(df) < 10:
                    return None
                highs = df['high'].values
                lows = df['low'].values
                close = df['close'].values
                if len(highs) < 5:
                    return None
                prev_high = highs[-4]
                prev_low = lows[-4]
                wick_high = highs[-3]
                wick_low = lows[-3]
                last_close = close[-2]
                bos_alcista = last_close > prev_high
                bos_bajista = last_close < prev_low
                barrido_alcista = wick_high > prev_high and close[-3] < wick_high
                barrido_bajista = wick_low < prev_low and close[-3] > wick_low
                if (bos_alcista and barrido_alcista) or (bos_bajista and barrido_bajista):
                    entrada = last_close
                    stop = prev_low if bos_alcista else prev_high
                    objetivo = close[-1] * (1.02 if bos_alcista else 0.98)
                    return {
                        'entrada': entrada,
                        'stop': stop,
                        'objetivo': objetivo,
                        'tipo': 'compra' if bos_alcista else 'venta'
                    }
                return None
            sim = SimuladorPatron(par['binance'], base_tf, patron_func_ict)
            # Validación de slippage y liquidez antes de agregar la señal
            size = gestor.calcular_tamano_operacion()
            side = 'buy' if tipo in ['compra', 'long'] else 'sell'
            ok_liq, slippage, motivo = estimar_slippage_y_liquidez(par['binance'], size, side)
            if mtf.validar(tipo) and sim.validar_operacion() and ok_liq:
                score = estimar_calidad_ict(ict)
                resultados.append({'estrategia': 'ICT', 'par': par['binance'], 'señal': ict.señal, 'score': score})
        # Ballena
        ballena = LiquidezBallena()
        ballena.symbol = par['binance']
        if ballena.ia_confirmacion():
            s = ballena.señal
            base_tf = s.get('timeframe', '15m') if s else '15m'
            tipo = s.get('tipo', 'long') if s else 'long'
            mtf = MultiTimeframeValidator(par['binance'], base_tf)
            def patron_func_ballena(df):
                # ...lógica realista...
                if len(df) < 15:
                    return None
                lows = df['low'].values
                highs = df['high'].values
                close = df['close'].values
                open_ = df['open'].values
                volume = df['volume'].values if 'volume' in df else np.ones(len(df))
                # Sweep bajista
                for i in range(10, len(lows)-5):
                    if all(abs(lows[i] - lows[i-j]) < 0.05 for j in range(1,4)):
                        idx = i
                        if lows[idx+1] < lows[idx] and volume[idx+1] > np.mean(volume[-30:])*1.5:
                            cuerpo = abs(close[idx+1] - open_[idx+1])
                            mecha = (close[idx+1] - lows[idx+1]) > cuerpo*2
                            engulfing = close[idx+2] > open_[idx+2] and close[idx+2] > close[idx+1]
                            if mecha or engulfing:
                                return {
                                    'entrada': close[idx+2],
                                    'stop': lows[idx+1] - 0.1,
                                    'target': close[idx+2] + abs(close[idx+2] - (lows[idx+1] - 0.1))*2.5,
                                    'tipo': 'long'
                                }
                # Sweep alcista
                for i in range(10, len(highs)-5):
                    if all(abs(highs[i] - highs[i-j]) < 0.05 for j in range(1,4)):
                        idx = i
                        if highs[idx+1] > highs[idx] and volume[idx+1] > np.mean(volume[-30:])*1.5:
                            cuerpo = abs(close[idx+1] - open_[idx+1])
                            mecha = (highs[idx+1] - close[idx+1]) > cuerpo*2
                            engulfing = close[idx+2] < open_[idx+2] and close[idx+2] < close[idx+1]
                            if mecha or engulfing:
                                return {
                                    'entrada': close[idx+2],
                                    'stop': highs[idx+1] + 0.1,
                                    'target': close[idx+2] - abs(highs[idx+1] + 0.1 - close[idx+2])*2.5,
                                    'tipo': 'short'
                                }
                return None
            sim = SimuladorPatron(par['binance'], base_tf, patron_func_ballena)
            size = gestor.calcular_tamano_operacion()
            side = 'buy' if tipo in ['compra', 'long'] else 'sell'
            ok_liq, slippage, motivo = estimar_slippage_y_liquidez(par['binance'], size, side)
            if mtf.validar(tipo) and sim.validar_operacion() and ok_liq:
                score = estimar_calidad_ballena(ballena)
                resultados.append({'estrategia': 'Ballena', 'par': par['binance'], 'señal': ballena.señal, 'score': score})
        # Arbitraje (solo para pares soportados)
        if par['binance'] in ['BTCUSDT', 'ETHUSDT']:
            arbitraje = ArbitrajeOculto()
            arbitraje.symbol_binance = par['binance']
            arbitraje.symbol_exness = par['exness']
            if arbitraje.ia_confirmacion():
                s = arbitraje.señal
                tipo = 'long' if s and s.get('comprar_en') == 'Binance' else 'short'
                mtf = MultiTimeframeValidator(par['binance'], '15m')
                def patron_func_arbitraje(df):
                    # ...lógica realista...
                    if len(df) < 10:
                        return None
                    close = df['close'].values
                    spread = (close[-1] - close[-2]) / close[-2] if close[-2] != 0 else 0
                    if tipo == 'long' and spread > 0.003:
                        return {
                            'entrada': close[-2],
                            'stop': close[-2] * 0.995,
                            'target': close[-2] * 1.003,
                            'tipo': 'long'
                        }
                    elif tipo == 'short' and spread < -0.003:
                        return {
                            'entrada': close[-2],
                            'stop': close[-2] * 1.005,
                            'target': close[-2] * 0.997,
                            'tipo': 'short'
                        }
                    return None
                sim = SimuladorPatron(par['binance'], '15m', patron_func_arbitraje)
                size = gestor.calcular_tamano_operacion()
                side = 'buy' if tipo in ['compra', 'long'] else 'sell'
                ok_liq, slippage, motivo = estimar_slippage_y_liquidez(par['binance'], size, side)
                if mtf.validar(tipo) and sim.validar_operacion() and ok_liq:
                    score = estimar_calidad_arbitraje(arbitraje)
                    resultados.append({'estrategia': 'Arbitraje', 'par': par['binance'], 'señal': arbitraje.señal, 'score': score})
    return resultados

def estimar_calidad_ict(ict):
    # Score simple: cuanto más lejos el objetivo del stop, mejor
    s = ict.señal
    if not s: return 0
    return abs(s.get('objetivo', 0) - s.get('entrada', 0)) / (abs(s.get('entrada', 1) - s.get('stop', 1)) + 1e-6)

def estimar_calidad_ballena(ballena):
    s = ballena.señal
    if not s: return 0
    return abs(s.get('target', 0) - s.get('entrada', 0)) / (abs(s.get('entrada', 1) - s.get('stop', 1)) + 1e-6)

def estimar_calidad_arbitraje(arbitraje):
    s = arbitraje.señal
    if not s: return 0
    return abs(s.get('potencial_beneficio', 0))

def diversificar_operaciones(gestor, capital_total):
    """
    Evalúa y ejecuta operaciones diversificadas en varios pares y estrategias.
    """
    resultados = evaluar_estrategias_y_activos(gestor, capital_total)
    if not resultados:
        return []
    # Normalizar scores para asignar capital proporcional
    scores = np.array([r['score'] for r in resultados])
    if scores.sum() == 0:
        pesos = np.ones_like(scores) / len(scores)
    else:
        pesos = scores / scores.sum()
    # Asignar capital y devolver señales listas para ejecutar
    operaciones = []
    for i, r in enumerate(resultados):
        capital_asignado = capital_total * pesos[i]
        op = {
            'estrategia': r['estrategia'],
            'par': r['par'],
            'señal': r['señal'],
            'capital': capital_asignado,
            'score': r['score']
        }
        operaciones.append(op)
    return operaciones
