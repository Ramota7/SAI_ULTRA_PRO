# --- CONSULTA DE SALDOS BINANCE SPOT Y FUTUROS USDT-M ---
def obtener_saldo_binance_spot(api_key, api_secret, asset='USDT'):
    """Devuelve el saldo disponible de un asset en Spot."""
    from binance.client import Client
    client = Client(api_key, api_secret)
    account = client.get_account()
    for a in account['balances']:
        if a['asset'] == asset:
            return float(a['free']) + float(a['locked'])
    return 0.0

def obtener_saldo_binance_futuros(api_key, api_secret, asset='USDT'):
    """Devuelve el saldo disponible de un asset en Futuros USDT-M."""
    from binance.client import Client
    client = Client(api_key, api_secret)
    balances = client.futures_account_balance()
    for b in balances:
        if b['asset'] == asset:
            return float(b['balance'])
    return 0.0

# --- ORDENES SPOT Y FUTUROS USDT-M ---
def enviar_orden_spot_binance(api_key, api_secret, simbolo, cantidad, side='BUY'):
    """Coloca una orden de mercado Spot (BUY o SELL)."""
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    client = Client(api_key, api_secret)
    try:
        if side == 'BUY':
            orden = client.order_market_buy(symbol=simbolo, quantity=cantidad)
        else:
            orden = client.order_market_sell(symbol=simbolo, quantity=cantidad)
        return orden
    except BinanceAPIException as e:
        print(f"[BINANCE][SPOT][ERROR] {e.status_code} {e.message}")
        return None

def enviar_orden_futuros_binance(api_key, api_secret, simbolo, cantidad, side='BUY', tipo='MARKET'):
    """Coloca una orden de mercado en Futuros USDT-M (BUY o SELL)."""
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    client = Client(api_key, api_secret)
    try:
        if side == 'BUY':
            orden = client.futures_create_order(symbol=simbolo, side='BUY', type=tipo, quantity=cantidad)
        else:
            orden = client.futures_create_order(symbol=simbolo, side='SELL', type=tipo, quantity=cantidad)
        return orden
    except BinanceAPIException as e:
        print(f"[BINANCE][FUTUROS][ERROR] {e.status_code} {e.message}")
        return None
def validar_api_exness(api_key, api_secret, server, platform):
    try:
        # Conexión real a Exness vía MetaTrader5
        if not mt5.initialize(server=server, login=int(api_key), password=api_secret):
            print(f"[ERROR] No se pudo conectar a Exness: {mt5.last_error()}")
            return False
        account_info = mt5.account_info()
        if account_info is not None:
            print(f"[VALIDACIÓN] Conexión a Exness OK | Usuario: {account_info.login} | Balance: {account_info.balance}")
            mt5.shutdown()
            return True
        else:
            print("[ERROR] Conexión a Exness fallida: No se pudo obtener información de la cuenta.")
            mt5.shutdown()
            return False
    except Exception as e:
        print(f"[ERROR] No se pudo conectar a Exness: {e}")
        return False

import time
import threading
from estrategias.ultra_rompimientos_ict import UltraRompimientosICT
from estrategias.filtros_señal import aplicar_filtros
import requests
import MetaTrader5 as mt5
def validar_api_binance(api_key, api_secret):
    """
    Verifica si las claves API de Binance son válidas usando una llamada privada (get_account).
    Muestra mensaje claro en consola.
    """
    try:
        from binance.client import Client
        from binance.exceptions import BinanceAPIException
        client = Client(api_key, api_secret)
        try:
            account = client.get_account()
            if 'balances' in account:
                print("[VALIDACIÓN] Claves API de Binance válidas (get_account OK)")
                return True
            else:
                print("[ERROR] Claves API de Binance inválidas: respuesta inesperada.")
                return False
        except BinanceAPIException as e:
            print(f"[ERROR] Claves API de Binance inválidas: {e.status_code} {e.message}")
            return False
        except Exception as e:
            print(f"[ERROR] Claves API de Binance inválidas: {e}")
            return False
    except Exception as e:
        print(f"[ERROR] No se pudo importar python-binance: {e}")
        return False
from estrategias.liquidez_ballena import LiquidezBallena
from estrategias.arbitraje_oculto import ArbitrajeOculto
from ia.analizador_volatilidad import AnalizadorVolatilidad
from gestion.gestor_riesgo_fases import GestorRiesgoFases
from integracion.telegram_alertas import enviar_alerta
from integracion.google_dashboard import registrar_operacion

def obtener_capital_binance(api_key, api_secret):
    # Consulta real del saldo en Binance usando python-binance
    try:
        from binance.client import Client
        client = Client(api_key, api_secret)
        account = client.get_account()
        for asset in account['balances']:
            if asset['asset'] == 'USDT':
                return float(asset['free']) + float(asset['locked'])
        print("[BINANCE][CAPITAL] No se encontró saldo USDT.")
        return None
    except Exception as e:
        print(f"[BINANCE][CAPITAL] Error: {e}")
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [BINANCE][CAPITAL] Error: {e}\n")
        return None

def obtener_capital_exness(api_key, api_secret):
    # Consulta real del saldo en Exness vía MetaTrader5, con validación de conexión y fallback controlado
    try:
        import MetaTrader5 as mt5
        login = None
        try:
            login = int(api_key)
        except Exception:
            msg = f"[EXNESS][CAPITAL] Login inválido: {api_key}"
            print(msg)
            with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
                from datetime import datetime
                flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
            return None
        if not mt5.initialize(login=login, password=api_secret):
            msg = f"[EXNESS][CAPITAL] No conectado"
            print(msg)
            with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
                from datetime import datetime
                flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
            return None
        info = mt5.account_info()
        if info:
            saldo = info.balance
            mt5.shutdown()
            return saldo
        else:
            msg = "[EXNESS][CAPITAL] No se pudo obtener info de cuenta."
            print(msg)
            with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
                from datetime import datetime
                flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
            mt5.shutdown()
            return None
    except Exception as e:
        msg = f"[EXNESS][CAPITAL] Excepción: {e}"
        print(msg)
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
        return None


# --- MODO OBSERVACIÓN ---
MODO_OBSERVACION = False  # Cambia a True para solo observar


# --- ORDEN REAL BINANCE ---

# --- ORDEN REAL BINANCE (COMPRA) ---
def enviar_orden_binance(api_key, api_secret, simbolo, cantidad):
    """
    Envía una orden de mercado BUY real a Binance usando python-binance.
    Valida parámetros, maneja errores y registra en consola y log.
    """
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    from datetime import datetime
    if MODO_OBSERVACION:
        print(f"[OBSERVACIÓN][BINANCE] Simulación de compra {cantidad} {simbolo}")
        return None
    if not simbolo or not isinstance(simbolo, str):
        print("[BINANCE][ORDEN COMPRA] Símbolo inválido.")
        return None
    try:
        cantidad = float(cantidad)
        if cantidad <= 0:
            print("[BINANCE][ORDEN COMPRA] Cantidad debe ser mayor a 0.")
            return None
    except Exception:
        print("[BINANCE][ORDEN COMPRA] Cantidad inválida.")
        return None
    try:
        client = Client(api_key, api_secret)
        orden = client.order_market_buy(symbol=simbolo, quantity=cantidad)
        status = orden.get('status', '')
        fills = orden.get('fills', [])
        precio_prom = sum(float(f['price'])*float(f['qty']) for f in fills) / sum(float(f['qty']) for f in fills) if fills else None
        qty_filled = orden.get('executedQty', '0')
        msg = f"[BINANCE][ORDEN COMPRA] {simbolo} BUY {cantidad} status={status} precio_prom={precio_prom} qty_filled={qty_filled}"
        print(msg)
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
        if status == 'FILLED':
            resumen = f"[BINANCE][ORDEN COMPRA FILLED] {simbolo} {qty_filled} a precio promedio {precio_prom}"
            try:
                from integracion.telegram_alertas import enviar_alerta
                enviar_alerta(resumen)
            except Exception:
                pass
        return orden
    except BinanceAPIException as e:
        err_msg = f"[BINANCE][ORDEN COMPRA][ERROR] {e.status_code} {e.message}"
        print(err_msg)
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {err_msg}\n")
        try:
            from integracion.telegram_alertas import enviar_alerta
            enviar_alerta(err_msg)
        except Exception:
            pass
        return None
    except Exception as e:
        err_msg = f"[BINANCE][ORDEN COMPRA][ERROR] {e}"
        print(err_msg)
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {err_msg}\n")
        return None

# --- ORDEN REAL BINANCE (VENTA) ---
def enviar_orden_venta_binance(api_key, api_secret, simbolo, cantidad):
    """
    Envía una orden de mercado SELL real a Binance usando python-binance.
    Valida parámetros, maneja errores y registra en consola y log.
    """
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    from datetime import datetime
    if MODO_OBSERVACION:
        print(f"[OBSERVACIÓN][BINANCE] Simulación de venta {cantidad} {simbolo}")
        return None
    if not simbolo or not isinstance(simbolo, str):
        print("[BINANCE][ORDEN VENTA] Símbolo inválido.")
        return None
    try:
        cantidad = float(cantidad)
        if cantidad <= 0:
            print("[BINANCE][ORDEN VENTA] Cantidad debe ser mayor a 0.")
            return None
    except Exception:
        print("[BINANCE][ORDEN VENTA] Cantidad inválida.")
        return None
    try:
        client = Client(api_key, api_secret)
        orden = client.order_market_sell(symbol=simbolo, quantity=cantidad)
        status = orden.get('status', '')
        fills = orden.get('fills', [])
        precio_prom = sum(float(f['price'])*float(f['qty']) for f in fills) / sum(float(f['qty']) for f in fills) if fills else None
        qty_filled = orden.get('executedQty', '0')
        msg = f"[BINANCE][ORDEN VENTA] {simbolo} SELL {cantidad} status={status} precio_prom={precio_prom} qty_filled={qty_filled}"
        print(msg)
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
        if status == 'FILLED':
            resumen = f"[BINANCE][ORDEN VENTA FILLED] {simbolo} {qty_filled} a precio promedio {precio_prom}"
            try:
                from integracion.telegram_alertas import enviar_alerta
                enviar_alerta(resumen)
            except Exception:
                pass
        return orden
    except BinanceAPIException as e:
        err_msg = f"[BINANCE][ORDEN VENTA][ERROR] {e.status_code} {e.message}"
        print(err_msg)
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {err_msg}\n")
        try:
            from integracion.telegram_alertas import enviar_alerta
            enviar_alerta(err_msg)
        except Exception:
            pass
        return None
    except Exception as e:
        err_msg = f"[BINANCE][ORDEN VENTA][ERROR] {e}"
        print(err_msg)
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {err_msg}\n")
        return None


def ejecutar_orden_exness(señal, size, api_key, api_secret, server=None, platform=None, symbol=None, price=None, sl=None, tp=None):
    import MetaTrader5 as mt5
    from datetime import datetime
    from integracion.google_dashboard import registrar_operacion
    if MODO_OBSERVACION:
        print(f"[OBSERVACIÓN][EXNESS] Señal: {señal} Tamaño: {size}")
        return True
    # Inicializar conexión real
    if not mt5.initialize(server=server, login=int(api_key), password=api_secret):
        print(f"[ERROR] No se pudo conectar a Exness: {mt5.last_error()}")
        return False
    # Preparar parámetros de la orden
    if symbol is None:
        print("[ERROR] No se especificó symbol para Exness.")
        mt5.shutdown()
        return False
    tipo_orden = mt5.ORDER_TYPE_BUY if señal.lower() == 'long' else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(size),
        "type": tipo_orden,
        "price": price if price else mt5.symbol_info_tick(symbol).ask,
        "sl": sl,
        "tp": tp,
        "deviation": 10,
        "magic": 20250728,
        "comment": f"IA SAI ULTRA PRO {datetime.now()}"
    }
    result = mt5.order_send(request)
    # Detectar error de margen insuficiente
    if hasattr(result, 'retcode') and result.retcode == 10019:
        msg = f"[EXNESS][ORDEN] Fallida por margen insuficiente (retcode=10019) en {symbol}. Sugerencia: cambiar símbolo o reducir volumen."
        print(msg)
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
    if result is None:
        print(f"[ERROR][EXNESS] mt5.order_send devolvió None. Último error: {mt5.last_error()}")
        mt5.shutdown()
        return False
    # Log completo de resultado para depuración
    print(f"[EXNESS][DEBUG] Resultado completo de order_send: {result}")
    if hasattr(result, 'retcode') and result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[ERROR][EXNESS] Fallo al ejecutar orden: {result.retcode} - {getattr(result, 'comment', '')}")
        mt5.shutdown()
        return False
    print(f"[EXNESS] Orden ejecutada: {result}")
    # Log y backup
    op_log = {
        'broker': 'exness',
        'symbol': symbol,
        'size': size,
        'señal': señal,
        'price': price,
        'sl': sl,
        'tp': tp,
        'retcode': result.retcode,
        'order': result.order,
        'comment': result.comment,
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    # Guardar en backup CSV
    import csv
    backup_path = 'sai_ultra_pro/ia/ops_exness.csv'
    file_exists = os.path.exists(backup_path)
    with open(backup_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(op_log.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(op_log)
    # Registrar en dashboard
    try:
        registrar_operacion(op_log)
    except Exception as e:
        print(f"[WARN] No se pudo registrar operación Exness en dashboard: {e}")
    mt5.shutdown()
    return True

# --- Prueba de conexión y operación Exness ---
def test_exness(api_key, api_secret, server, platform, symbol):
    print("[TEST] Probando conexión y operación con Exness...")
    import MetaTrader5 as mt5
    if not mt5.initialize(server=server, login=int(api_key), password=api_secret):
        print(f"[ERROR][TEST] No se pudo conectar a Exness: {mt5.last_error()}")
        return False
    info = mt5.account_info()
    if info:
        print(f"[TEST] Conexión OK. Usuario: {info.login} | Balance: {info.balance}")
    else:
        print("[ERROR][TEST] No se pudo obtener info de cuenta Exness.")
        mt5.shutdown()
        return False
    # Prueba de orden (simulada, sin ejecución real)
    print(f"[TEST] Simulando orden BUY 0.01 {symbol}...")
    price = mt5.symbol_info_tick(symbol).ask
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY,
        "price": price,
        "deviation": 10,
        "magic": 20250728,
        "comment": "TEST SAI ULTRA PRO"
    }
    # No enviar la orden real, solo mostrar request
    print(f"[TEST] Request: {request}")
    mt5.shutdown()
    return True

import json
import shap
import os
import pandas as pd
def ciclo():

    # --- Auditoría y alerta de rotación de claves API ---
    try:
        from datetime import datetime, timedelta
        audit_path = 'sai_ultra_pro/ia/api_audit.log'
        now = datetime.now()
        rotated = False
        if os.path.exists(audit_path):
            with open(audit_path, 'r') as f:
                lines = f.readlines()
                fechas = [l.split('|')[0].strip() for l in lines if 'rotada' in l]
                if fechas:
                    last_rot = max([datetime.strptime(f, '%Y-%m-%d %H:%M:%S.%f') for f in fechas])
                    if (now - last_rot).days > 30:
                        enviar_alerta('[AUDITORÍA] Las claves API no se han rotado en más de 30 días.')
        # Registrar uso
        with open(audit_path, 'a') as f:
            f.write(f'{now} | uso ciclo principal\n')
    except Exception as e:
        enviar_alerta(f'[AUDITORÍA] Error en auditoría de claves: {e}')
    # --- Selección dinámica de activo favorable ---
    from estrategias.seleccion_activo import seleccionar_activo_favorable
    def tendencia_func(symbol):
        # Ejemplo simple: siempre True (personaliza según tu lógica)
        return True
    def ia_func(symbol):
        # Ejemplo simple: siempre True (conecta tu IA real aquí)
        return True
    activo, score, motivos = seleccionar_activo_favorable(tendencia_func, ia_func)
    if activo:
        print(f"[SELECCIÓN ACTIVO] Seleccionado: {activo['symbol']} | Score: {score} | Motivos: {motivos}")
        # --- ORDEN REAL: Compra cualquier símbolo con score > 0.7 y volatilidad aceptable ---
        if score > 0.7 and activo.get('volatilidad', 'normal') in ['normal', 'baja']:
            with open('sai_ultra_pro/config/config.json') as f:
                config = json.load(f)
            api_binance = config.get('api_keys', {}).get('binance', '')
            api_binance_secret = config.get('api_keys', {}).get('binance_secret', '')
            simbolo = activo['symbol']
            cantidad = 0.01 if simbolo == 'ETHUSDT' else 0.001 if simbolo == 'BTCUSDT' else 1
            enviar_orden_binance(api_binance, api_binance_secret, simbolo, cantidad)
            # Simulación de posición abierta (puedes adaptar a tu lógica real)
            global posicion_abierta
            posicion_abierta = {'simbolo': simbolo, 'cantidad': cantidad}
    else:
        print("[SELECCIÓN ACTIVO] No se pudo seleccionar un activo favorable.")

    # --- Cierre de posición al final del ciclo (ejemplo) ---
    try:
        if 'posicion_abierta' in globals() and posicion_abierta:
            with open('sai_ultra_pro/config/config.json') as f:
                config = json.load(f)
            api_binance = config.get('api_keys', {}).get('binance', '')
            api_binance_secret = config.get('api_keys', {}).get('binance_secret', '')
            simbolo = posicion_abierta['simbolo']
            cantidad = posicion_abierta['cantidad']
            enviar_orden_venta_binance(api_binance, api_binance_secret, simbolo, cantidad)
            posicion_abierta = None
    except Exception as e:
        print(f"[BINANCE][ORDEN VENTA][ERROR] Error al cerrar posición: {e}")
    try:
        with open('sai_ultra_pro/config/config.json') as f:
            config = json.load(f)
    except Exception as e:
        print(f"[ERROR] No se pudo cargar config.json: {e}")
        enviar_alerta(f"[ERROR] No se pudo cargar config.json: {e}")
        return
    activos = config.get('activos', ['BTCUSDT'])
    api_binance = config.get('api_keys', {}).get('binance', '')
    api_exness = config.get('api_keys', {}).get('exness', '')
    api_binance_secret = config.get('api_keys', {}).get('binance_secret', '')
    api_exness_secret = config.get('api_keys', {}).get('exness_secret', '')


    # --- Validación robusta de entorno y failover automático entre brokers ---
    from ia.analizador_volatilidad_exness import AnalizadorVolatilidadExness
    symbols_exness = ['USDRUB', 'USDAED', 'USDBRL', 'US30m', 'US500m', 'USTECm']  # Puedes parametrizar
    entorno_binance = {}
    entorno_exness = {}
    broker_binance_ok = True
    broker_exness_ok = True
    # Validar entorno y conexión Binance
    try:
        for symbol in activos:
            av = AnalizadorVolatilidad()
            av.symbol = symbol
            entorno_binance[symbol] = av.evaluar_entorno()
            print(f"[VALIDACIÓN ENTORNO][BINANCE] {symbol}: {entorno_binance[symbol]}")
            if entorno_binance[symbol] == 'riesgo alto':
                enviar_alerta(f"[ALERTA] Entorno de riesgo alto en Binance para {symbol}. No se operará.")
                broker_binance_ok = False
    except Exception as e:
        enviar_alerta(f"[FAILOVER] Error crítico en entorno/conexión Binance: {e}")
        broker_binance_ok = False
    # Validar entorno y conexión Exness
    try:
        for symbol in symbols_exness:
            avx = AnalizadorVolatilidadExness(symbol=symbol)
            entorno_exness[symbol] = avx.evaluar_entorno()
            print(f"[VALIDACIÓN ENTORNO][EXNESS] {symbol}: {entorno_exness[symbol]}")
            if entorno_exness[symbol] == 'riesgo alto':
                enviar_alerta(f"[ALERTA] Entorno de riesgo alto en Exness para {symbol}. No se operará.")
                broker_exness_ok = False
    except Exception as e:
        enviar_alerta(f"[FAILOVER] Error crítico en entorno/conexión Exness: {e}")
        broker_exness_ok = False

    # Failover: si un broker falla, operar solo con el otro
    if not broker_binance_ok and not broker_exness_ok:
        enviar_alerta("[CRÍTICO] Ambos brokers no están operativos. No se operará en este ciclo.")
        return
    elif not broker_binance_ok:
        enviar_alerta("[FAILOVER] Solo Exness está operativo. Todas las operaciones irán a Exness.")
        activos = []  # No operar en Binance
    elif not broker_exness_ok:
        enviar_alerta("[FAILOVER] Solo Binance está operativo. Todas las operaciones irán a Binance.")
        symbols_exness = []  # No operar en Exness

    # --- Validación de datos antes de entrenar u operar ---
    def validar_datos(df, nombre):
        if df is None or len(df) == 0:
            enviar_alerta(f"[DATOS] {nombre}: DataFrame vacío o None.")
            return False
        if df.isnull().any().any():
            enviar_alerta(f"[DATOS] {nombre}: Hay valores NaN en los datos.")
            return False
        if (df.select_dtypes(include=[float, int]) > 1e8).any().any():
            enviar_alerta(f"[DATOS] {nombre}: Outliers extremos detectados.")
            return False
        return True

    # 0. Backtesting obligatorio antes de operar
    try:
        from ia.backtesting import cargar_datos, simular_trading
        from keras.models import load_model
        df_bt = cargar_datos('data_BTCUSDT_15m.csv')
        modelo_bt = load_model(os.path.join(os.path.dirname(__file__), 'ia/modelo_transformer.h5'))
        with open('sai_ultra_pro/config/config.json') as f:
            config_bt = json.load(f)
        threshold_bt = config_bt.get('umbral_ia', 0.6)
        ops_bt, balance_bt = simular_trading(df_bt, modelo_bt, threshold=threshold_bt)
        winrate_bt = 100*sum(ops_bt['resultado']=='TP')/len(ops_bt) if len(ops_bt)>0 else 0
        resumen_bt = f"[BACKTEST] Winrate: {winrate_bt:.1f}% | Capital final: {balance_bt[-1]:.2f} | Operaciones: {len(ops_bt)}"
        print(resumen_bt)
        enviar_alerta(resumen_bt)
    except Exception as e:
        enviar_alerta(f"[ERROR BACKTEST] {e}")

def main():
    # --- Reentrenamiento automático semanal y por eventos de mercado ---
    from ia.analizador_volatilidad import AnalizadorVolatilidad
    import numpy as np
    import shutil
    from ia.entrenar_modelo import entrenar_modelo
    from ia.backtesting import cargar_datos, simular_trading
    from keras.models import load_model
    from integracion.telegram_alertas import enviar_alerta
    import threading
    import time
    def walk_forward(df, modelo, window=20, threshold=0.6, step=100):
        n = len(df)
        resultados = []
        for start in range(0, n-window-10, step):
            sub = df.iloc[start:start+step+window+10]
            if len(sub) < window+10:
                continue
            ops, balance = simular_trading(sub, modelo, window=window, threshold=threshold)
            if len(ops) > 0:
                winrate = 100*sum(ops['resultado']=='TP')/len(ops)
                dd = (np.max(balance)-balance[-1])/np.max(balance) if np.max(balance)>0 else 0
                profit_factor = (ops['capital'].iloc[-1]-ops['capital'].iloc[0])/abs(ops['capital'].iloc[0]) if ops['capital'].iloc[0]!=0 else 0
                resultados.append({'winrate':winrate,'drawdown':dd,'profit_factor':profit_factor,'ops':len(ops)})
        return resultados

    def reentrenar_modelo_automatico():
        activos = ['BTCUSDT','ETHUSDT','BNBUSDT']
        timeframes = ['15m','1h']
        umbral_winrate = 55
        umbral_drawdown = 0.18
        umbral_profit = 0.01
        umbral_ops = 10
        modelo_path = os.path.join(os.path.dirname(__file__), 'ia/modelo_transformer.h5')
        modelo_backup = os.path.join(os.path.dirname(__file__), 'ia/modelo_transformer_backup.h5')
        resumen_telegram = '[VALIDACIÓN IA]\n'
        # --- Bucle principal ---
        while True:
            try:
                # --- Reentrenamiento por eventos de mercado ---
                evento_detectado = False
                for symbol in activos:
                    for tf in timeframes:
                        av = AnalizadorVolatilidad()
                        av.symbol = symbol
                        av.timeframe = tf
                        entorno = av.evaluar_entorno()
                        candles = av.obtener_candles(limit=100)
                        close = candles[:,4].astype(float)
                        high = candles[:,2].astype(float)
                        volume = candles[:,5].astype(float)
                        # Detectar nuevo máximo local (última vela mayor que las 20 previas)
                        if len(close) > 20 and close[-1] > np.max(close[-21:-1]):
                            evento_detectado = True
                            enviar_alerta(f'[EVENTO] Nuevo máximo detectado en {symbol}-{tf}')
                        # Detectar volumen alto (última vela > 2x volumen medio)
                        if len(volume) > 20 and volume[-1] > 2*np.mean(volume[-21:-1]):
                            evento_detectado = True
                            enviar_alerta(f'[EVENTO] Volumen alto detectado en {symbol}-{tf}')
                        # Detectar cambio de entorno
                        if entorno == 'riesgo alto':
                            evento_detectado = True
                            enviar_alerta(f'[EVENTO] Cambio de entorno a riesgo alto en {symbol}-{tf}')
                if evento_detectado:
                    enviar_alerta('[AUTO] Reentrenando modelo IA por evento de mercado...')
                    entrenar_modelo()
                # --- Reentrenamiento semanal ---
                now = time.time()
                retrain_flag_path = 'sai_ultra_pro/ia/last_retrain.txt'
                last_retrain = 0
                if os.path.exists(retrain_flag_path):
                    with open(retrain_flag_path, 'r') as f:
                        try:
                            last_retrain = float(f.read().strip())
                        except:
                            last_retrain = 0
                if now - last_retrain > 7*24*3600:
                    enviar_alerta('[AUTO] Reentrenamiento semanal del modelo IA...')
                    entrenar_modelo()
                    with open(retrain_flag_path, 'w') as fw:
                        fw.write(str(now))
                # --- Validación IA tras reentrenamiento (cada ciclo) ---
                passed = True
                for symbol in activos:
                    for tf in timeframes:
                        nombre = f'data_{symbol}_{tf}.csv'
                        try:
                            df_bt = cargar_datos(nombre)
                            modelo_bt = load_model(os.path.join(os.path.dirname(__file__), 'ia/modelo_transformer.h5'))
                            threshold_bt = 0.6
                            resultados = walk_forward(df_bt, modelo_bt, threshold=threshold_bt)
                        except Exception as e:
                            resumen_telegram += f'- {symbol}-{tf}: Error {e}\n'
                            passed = False
                            continue
                        if not resultados:
                            resumen_telegram += f'- {symbol}-{tf}: Sin resultados suficientes\n'
                            passed = False
                            continue
                        winrates = [r['winrate'] for r in resultados]
                        dds = [r['drawdown'] for r in resultados]
                        profits = [r['profit_factor'] for r in resultados]
                        opss = [r['ops'] for r in resultados]
                        resumen_telegram += f'- {symbol}-{tf}: Winrate {np.mean(winrates):.1f}%, DD {np.max(dds)*100:.1f}%, PF {np.mean(profits):.2f}, Ops {int(np.mean(opss))}\n'
                        if np.max(dds) > 0.25:
                            umbral_winrate = max(umbral_winrate-5, 50)
                            umbral_drawdown = min(umbral_drawdown+0.03, 0.25)
                        elif np.max(dds) < 0.10:
                            umbral_winrate = min(umbral_winrate+5, 65)
                            umbral_drawdown = max(umbral_drawdown-0.03, 0.10)
                        if np.mean(winrates) < umbral_winrate or np.max(dds) > umbral_drawdown or np.mean(profits) < umbral_profit or np.mean(opss) < umbral_ops:
                            passed = False
                if not passed:
                    if os.path.exists(modelo_backup):
                        shutil.copy(modelo_backup, modelo_path)
                    resumen_telegram += '\n[ALERTA] El modelo NO pasó la validación. Se restauró el modelo anterior.'
                else:
                    shutil.copy(modelo_path, modelo_backup)
                enviar_alerta(resumen_telegram)
                time.sleep(600)  # Espera 10 minutos entre ciclos
            except Exception as e:
                enviar_alerta(f'[AUTO] Error en reentrenamiento automático: {e}')
                time.sleep(600)
    hilo_reentrenamiento = threading.Thread(target=reentrenar_modelo_automatico, daemon=True)
    hilo_reentrenamiento.start()


    # 6. Registro de operaciones y resumen detallado

    try:
        resumen = f"[RESUMEN SAI ULTRA PRO]\n"
        entorno = "Producción"  # O asigna el valor adecuado según tu lógica
        resumen += f"Entorno: {entorno}\n"
        # Definir capital_binance, capital_exness y capital_total antes de usarlos
        # Leer las claves API desde config.json
        with open('sai_ultra_pro/config/config.json') as f:
            config_resumen = json.load(f)
        api_binance = config_resumen.get('api_keys', {}).get('binance', '')
        api_exness = config_resumen.get('api_keys', {}).get('exness', '')
        api_binance_secret = config_resumen.get('api_keys', {}).get('binance_secret', '')
        api_exness_secret = config_resumen.get('api_keys', {}).get('exness_secret', '')
        capital_binance = obtener_capital_binance(api_binance, api_binance_secret)
        capital_exness = obtener_capital_exness(api_exness, api_exness_secret)
        capital_total = capital_binance + capital_exness
        resumen += f"Capital Binance: {capital_binance} | Exness: {capital_exness} | Total: {capital_total}\n"
        resumen += "Fase/Riesgo: N/D\n"
        operaciones = []  # Definir operaciones como lista vacía o cargar según tu lógica
        if operaciones:
            for op in operaciones:
                resumen += f"\n--- Operación ejecutada ---\n"
                for k, v in op.get('señal', {}).items():
                    resumen += f"{k}: {v}\n"
                resumen += f"Estrategia: {op.get('estrategia','N/D')} | Par: {op.get('par','N/D')} | Capital: {op.get('capital',0):.2f} | Score: {op.get('score',0):.2f}\n"
        else:
            resumen += "\nNo se ejecutó ninguna señal en este ciclo.\n"
    except Exception as e:
        resumen = f"[RESUMEN SAI ULTRA PRO]\n[ERROR] Error generando resumen: {e}\n"

    # --- Registro de operación con drawdown y racha ---
    try:
        from datetime import datetime, timedelta
        import csv
        import threading
        ops_path = 'sai_ultra_pro/ia/ops_real.csv'
        historial = []
        if os.path.exists(ops_path):
            with open(ops_path, 'r') as f:
                reader = csv.DictReader(f)
                historial = list(reader)
        capital = capital_total
        max_cap = max([float(op['capital']) for op in historial], default=capital)
        drawdown = round((max_cap-capital)/max_cap, 4) if max_cap > 0 else 0
        racha = 0
        if historial:
            for op in reversed(historial):
                if op.get('resultado','') == 'TP':
                    if racha < 0: break
                    racha += 1
                elif op.get('resultado','') == 'SL':
                    if racha > 0: break
                    racha -= 1
        # Guardar registro de cada operación
        from csv import writer as csv_writer
        with open(ops_path, 'a', newline='') as f:
            writer = csv_writer(f)
            for op in operaciones:
                try:
                    writer.writerow([
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        capital,
                        op.get('señal',{}).get('resultado', 'pendiente'),
                        drawdown,
                        racha
                    ])
                except Exception as e:
                    print(f"[WARN] No se pudo registrar operación en CSV: {e}")
        for op in operaciones:
            try:
                registrar_operacion(op)
            except Exception as e:
                print(f"[WARN] No se pudo registrar operación en dashboard: {e}")
        enviar_alerta(resumen + f"\nDrawdown: {drawdown*100:.2f}% | Racha: {racha}")

        # --- Reentrenamiento automático por desempeño ---
        winrate = None
        if os.path.exists(ops_path):
            try:
                import pandas as pd
                df_ops = pd.read_csv(ops_path, names=["fecha","capital","resultado","drawdown","racha"], header=0)
                total_ops = len(df_ops)
                if total_ops >= 20:
                    winrate = 100*sum(df_ops['resultado']=='TP')/total_ops
            except Exception as e:
                print(f"[WARN] No se pudo calcular winrate para reentrenamiento: {e}")

        trigger_retrain = False
        if winrate is not None and winrate < 55:
            trigger_retrain = True
        if drawdown > 0.15:
            trigger_retrain = True
        if racha < -4:
            trigger_retrain = True
        if trigger_retrain:
            enviar_alerta('[AUTO] Reentrenando modelo IA por bajo desempeño...')
            def retrain_thread():
                from ia.entrenar_modelo import entrenar_modelo
                entrenar_modelo()
            threading.Thread(target=retrain_thread, daemon=True).start()

        # --- Reentrenamiento automático cada 7 días ---
        retrain_flag_path = 'sai_ultra_pro/ia/last_retrain.txt'
        now = datetime.now()
        last_retrain = None
        if os.path.exists(retrain_flag_path):
            with open(retrain_flag_path, 'r') as f:
                try:
                    last_retrain = datetime.strptime(f.read().strip(), '%Y-%m-%d %H:%M:%S')
                except:
                    last_retrain = None
        if not last_retrain or (now - last_retrain) > timedelta(days=7):
            enviar_alerta('[AUTO] Reentrenamiento semanal del modelo IA...')
            def retrain_thread():
                from ia.entrenar_modelo import entrenar_modelo
                entrenar_modelo()
                with open(retrain_flag_path, 'w') as fw:
                    fw.write(now.strftime('%Y-%m-%d %H:%M:%S'))
            threading.Thread(target=retrain_thread, daemon=True).start()

    except Exception as e:
        print(f"[ERROR] Error en registro de operaciones/resumen: {e}")
        enviar_alerta(f"[ERROR] Error en registro de operaciones/resumen: {e}")



def main():
    # --- Reentrenamiento automático semanal del modelo IA ---

    def reentrenar_modelo_automatico():
        from ia.entrenar_modelo import entrenar_modelo
        from ia.backtesting import cargar_datos, simular_trading
        from keras.models import load_model
        import shutil
        import numpy as np
        from integracion.telegram_alertas import enviar_alerta
        def walk_forward(df, modelo, window=20, threshold=0.6, step=100):
            # Divide el dataset en bloques y evalúa el modelo en cada uno
            n = len(df)
            resultados = []
            for start in range(0, n-window-10, step):
                sub = df.iloc[start:start+step+window+10]
                if len(sub) < window+10:
                    continue
                ops, balance = simular_trading(sub, modelo, window=window, threshold=threshold)
                if len(ops) > 0:
                    winrate = 100*sum(ops['resultado']=='TP')/len(ops)
                    dd = (np.max(balance)-balance[-1])/np.max(balance) if np.max(balance)>0 else 0
                    profit_factor = (ops['capital'].iloc[-1]-ops['capital'].iloc[0])/abs(ops['capital'].iloc[0]) if ops['capital'].iloc[0]!=0 else 0
                    resultados.append({'winrate':winrate,'drawdown':dd,'profit_factor':profit_factor,'ops':len(ops)})
            return resultados
        while True:
            try:
                print('[AUTO] Descargando datos y reentrenando modelo IA...')
                entrenar_modelo()
                activos = ['BTCUSDT','ETHUSDT','BNBUSDT']
                timeframes = ['15m','1h']
                umbral_winrate = 55
                umbral_drawdown = 0.18
                umbral_profit = 0.01
                umbral_ops = 10

                passed = True
                resumen_telegram = '[VALIDACIÓN IA]\n'
                passed = True
                for symbol in activos:
                    for tf in timeframes:
                        nombre = f'data_{symbol}_{tf}.csv'
                        try:
                            df_bt = cargar_datos(nombre)
                            modelo_bt = load_model(os.path.join(os.path.dirname(__file__), 'ia/modelo_transformer.h5'))
                            threshold_bt = 0.6
                            resultados = walk_forward(df_bt, modelo_bt, threshold=threshold_bt)
                        except Exception as e:
                            resumen_telegram += f'- {symbol}-{tf}: Error {e}\n'
                            passed = False
                            continue
                        if not resultados:
                            resumen_telegram += f'- {symbol}-{tf}: Sin resultados suficientes\n'
                            passed = False
                            continue
                        winrates = [r['winrate'] for r in resultados]
                        dds = [r['drawdown'] for r in resultados]
                        profits = [r['profit_factor'] for r in resultados]
                        opss = [r['ops'] for r in resultados]
                        resumen_telegram += f'- {symbol}-{tf}: Winrate {np.mean(winrates):.1f}%, DD {np.max(dds)*100:.1f}%, PF {np.mean(profits):.2f}, Ops {int(np.mean(opss))}\n'
                        # Umbrales adaptativos: si la volatilidad es alta, relaja winrate, si es baja, exige más
                        if np.max(dds) > 0.25:
                            umbral_winrate = max(umbral_winrate-5, 50)
                            umbral_drawdown = min(umbral_drawdown+0.03, 0.25)
                        elif np.max(dds) < 0.10:
                            umbral_winrate = min(umbral_winrate+5, 65)
                            umbral_drawdown = max(umbral_drawdown-0.03, 0.10)
                        # Validación
                        if np.mean(winrates) < umbral_winrate or np.max(dds) > umbral_drawdown or np.mean(profits) < umbral_profit or np.mean(opss) < umbral_ops:
                            passed = False
                # Backup del modelo anterior si el nuevo falla
                modelo_path = os.path.join(os.path.dirname(__file__), 'ia/modelo_transformer.h5')
                modelo_backup = os.path.join(os.path.dirname(__file__), 'ia/modelo_transformer_backup.h5')
                if not passed:
                    if os.path.exists(modelo_backup):
                        shutil.copy(modelo_backup, modelo_path)
                    resumen_telegram += '\n[ALERTA] El modelo NO pasó la validación. Se restauró el modelo anterior.'
                else:
                    shutil.copy(modelo_path, modelo_backup)
                enviar_alerta(resumen_telegram)
                time.sleep(604800)
            except Exception as e:
                enviar_alerta(f'[AUTO] Error en reentrenamiento automático: {e}')
                time.sleep(3600)
    # Lanzar reentrenamiento automático en hilo aparte
    hilo_reentrenamiento = threading.Thread(target=reentrenar_modelo_automatico, daemon=True)
    hilo_reentrenamiento.start()
    with open('sai_ultra_pro/config/config.json') as f:
        config = json.load(f)
    api_binance = config['api_keys'].get('BINANCE_API_KEY', '')
    api_binance_secret = config['api_keys'].get('BINANCE_API_SECRET', '')
    api_exness = config['api_keys'].get('EXNESS_API_KEY', '')
    api_exness_secret = config['api_keys'].get('EXNESS_API_SECRET', '')
    exness_server = config['api_keys'].get('EXNESS_SERVER', '')
    exness_platform = config['api_keys'].get('EXNESS_PLATFORM', '')

    print("[VALIDACIÓN] Probando conexión con APIs...")
    ok_binance = validar_api_binance(api_binance, api_binance_secret)
    ok_exness = validar_api_exness(api_exness, api_exness_secret, exness_server, exness_platform)
    if not ok_binance or not ok_exness:
        print("[ERROR] No se pudo validar la conexión con las APIs. Corrige las credenciales o la red antes de operar en real.")
        return

    accuracy_real = []
    config_path = 'sai_ultra_pro/config/config.json'
    # Leer umbral, riesgo y sensibilidad desde config.json
    with open(config_path) as f:
        config = json.load(f)
    umbral_ia = config.get('umbral_ia', 0.6)
    riesgo_base = config.get('riesgo_base', 0.01)
    sensibilidad = config.get('sensibilidad_ajuste', 0.05)
    acc_bajo = config.get('umbral_acc_bajo', 0.5)
    acc_alto = config.get('umbral_acc_alto', 0.65)
    # Parámetros para autoajuste de sensibilidad y umbrales
    min_sens = 0.01
    max_sens = 0.15
    min_acc_bajo = 0.4
    max_acc_alto = 0.8
    # --- Gestión dinámica y autoajuste de umbrales de drawdown y racha ---
    ops_path = 'sai_ultra_pro/ia/ops_real.csv'
    drawdown = 0
    racha = 0
    # Umbrales autoajustables
    umbral_drawdown = config.get('umbral_drawdown', 0.15)
    umbral_racha_neg = config.get('umbral_racha_neg', -4)
    umbral_racha_pos = config.get('umbral_racha_pos', 5)
    # Analizar historial reciente para autoajustar umbrales
    if os.path.exists(ops_path):
        import csv
        with open(ops_path, 'r') as f:
            reader = list(csv.DictReader(f))
            if reader:
                max_cap = max([float(op['capital']) for op in reader])
                capital = float(reader[-1]['capital'])
                drawdown = round((max_cap-capital)/max_cap, 4) if max_cap > 0 else 0
                # Calcular racha
                for op in reversed(reader):
                    if op['resultado'] == 'TP':
                        if racha < 0: break
                        racha += 1
                    elif op['resultado'] == 'SL':
                        if racha > 0: break
                        racha -= 1
                # Autoajuste de umbrales según volatilidad y resultados recientes
                ultimos = reader[-30:] if len(reader) > 30 else reader
                dd_hist = [round((max([float(op['capital']) for op in ultimos[:i+1]])-float(op['capital']))/max([float(op['capital']) for op in ultimos[:i+1]]),4) if max([float(op['capital']) for op in ultimos[:i+1]])>0 else 0 for i,op in enumerate(ultimos)]
                max_dd = max(dd_hist) if dd_hist else 0
                if max_dd > 0.2:
                    umbral_drawdown = min(umbral_drawdown+0.02, 0.25)
                elif max_dd < 0.1:
                    umbral_drawdown = max(umbral_drawdown-0.01, 0.10)
                # Ajustar umbral de racha negativa si hay muchas rachas largas
                rachas_neg = 0
                racha_tmp = 0
                for op in ultimos:
                    if op['resultado']=='SL':
                        racha_tmp -= 1
                        if racha_tmp < umbral_racha_neg:
                            rachas_neg += 1
                    else:
                        racha_tmp = 0
                if rachas_neg > 2:
                    umbral_racha_neg -= 1
                elif rachas_neg == 0:
                    umbral_racha_neg = min(umbral_racha_neg+1, -2)
                # Ajustar umbral de racha positiva si hay muchas rachas largas
                rachas_pos = 0
                racha_tmp = 0
                for op in ultimos:
                    if op['resultado']=='TP':
                        racha_tmp += 1
                        if racha_tmp > umbral_racha_pos:
                            rachas_pos += 1
                    else:
                        racha_tmp = 0
                if rachas_pos > 2:
                    umbral_racha_pos += 1
                elif rachas_pos == 0:
                    umbral_racha_pos = max(umbral_racha_pos-1, 3)
    # Guardar umbrales autoajustados
    config['umbral_drawdown'] = umbral_drawdown
    config['umbral_racha_neg'] = umbral_racha_neg
    config['umbral_racha_pos'] = umbral_racha_pos
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    # Ajuste de riesgo por drawdown/racha usando umbrales autoajustados
    riesgo_base_orig = riesgo_base
    if drawdown > umbral_drawdown:
        riesgo_base = max(riesgo_base * 0.5, 0.003)
        enviar_alerta(f'[GESTIÓN RIESGO] Drawdown elevado ({drawdown*100:.1f}%). Riesgo reducido a {riesgo_base:.3f}.')
    elif racha <= umbral_racha_neg:
        riesgo_base = max(riesgo_base * 0.7, 0.003)
        enviar_alerta(f'[GESTIÓN RIESGO] Racha negativa de {racha} operaciones. Riesgo reducido a {riesgo_base:.3f}.')
    elif racha >= umbral_racha_pos and drawdown < 0.05:
        riesgo_base = min(riesgo_base * 1.2, 0.07)
        enviar_alerta(f'[GESTIÓN RIESGO] Racha positiva de {racha} operaciones. Riesgo aumentado a {riesgo_base:.3f}.')
    if riesgo_base != riesgo_base_orig:
        config['riesgo_base'] = riesgo_base
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    while True:
        # Actualizar config.json con los umbrales actuales antes de cada ciclo
        with open(config_path) as f:
            config = json.load(f)
        config['umbral_ia'] = umbral_ia
        config['riesgo_base'] = riesgo_base
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        ciclo()
        # Lógica de monitorización y ajuste automático
        try:
            if os.path.exists('sai_ultra_pro/ia/ops_real.csv'):
                df = pd.read_csv('sai_ultra_pro/ia/ops_real.csv')
                if len(df) > 50:
                    acc = (df['resultado']=='TP').mean()
                    accuracy_real.append(acc)
                    from integracion.telegram_alertas import enviar_alerta
                    # Ajuste automático de umbral IA y riesgo en config.json
                    if acc < acc_bajo:
                        umbral_ia = min(umbral_ia + sensibilidad, 0.9)
                        riesgo_base = max(riesgo_base * (1-sensibilidad), 0.005)
                        # Si el accuracy bajo persiste, aumentar sensibilidad y bajar umbral_acc_bajo
                        sensibilidad = min(sensibilidad + 0.01, max_sens)
                        acc_bajo = max(acc_bajo - 0.01, min_acc_bajo)
                        config['umbral_ia'] = umbral_ia
                        config['riesgo_base'] = riesgo_base
                        config['sensibilidad_ajuste'] = sensibilidad
                        config['umbral_acc_bajo'] = acc_bajo
                        with open(config_path, 'w') as f:
                            json.dump(config, f, indent=2)
                        enviar_alerta(f'[ALERTA] Accuracy bajo ({acc:.2f}). Umbral IA subido a {umbral_ia:.2f}, riesgo reducido a {riesgo_base:.3f}. Sensibilidad aumentada a {sensibilidad:.3f}, umbral_acc_bajo a {acc_bajo:.2f}. Bot pausado para revisión.\nRecomendación: Revisa el modelo, los datos y los logs de SHAP. Considera reentrenar o ajustar features.')
                        break
                    elif acc > acc_alto:
                        umbral_ia = max(umbral_ia - sensibilidad, 0.5)
                        riesgo_base = min(riesgo_base * (1+sensibilidad), 0.05)
                        # Si el accuracy alto persiste, reducir sensibilidad y subir umbral_acc_alto
                        sensibilidad = max(sensibilidad - 0.01, min_sens)
                        acc_alto = min(acc_alto + 0.01, max_acc_alto)
                        config['umbral_ia'] = umbral_ia
                        config['riesgo_base'] = riesgo_base
                        config['sensibilidad_ajuste'] = sensibilidad
                        config['umbral_acc_alto'] = acc_alto
                        with open(config_path, 'w') as f:
                            json.dump(config, f, indent=2)
                        enviar_alerta(f'[INFO] Accuracy alto ({acc:.2f}). Umbral IA bajado a {umbral_ia:.2f}, riesgo aumentado a {riesgo_base:.3f}. Sensibilidad reducida a {sensibilidad:.3f}, umbral_acc_alto a {acc_alto:.2f}.\nRecomendación: Puedes mantener el modelo, pero sigue monitoreando el drawdown y la calidad de las señales.')
                    else:
                        # Si el sistema está estable, suavizar sensibilidad y umbrales hacia valores medios
                        sensibilidad = max(min((sensibilidad + 0.05) / 2, max_sens), min_sens)
                        acc_bajo = min(max((acc_bajo + 0.5) / 2, min_acc_bajo), 0.5)
                        acc_alto = max(min((acc_alto + 0.65) / 2, max_acc_alto), 0.65)
                        config['sensibilidad_ajuste'] = sensibilidad
                        config['umbral_acc_bajo'] = acc_bajo
                        config['umbral_acc_alto'] = acc_alto
                        with open(config_path, 'w') as f:
                            json.dump(config, f, indent=2)
                        enviar_alerta(f'[INFO] Accuracy estable ({acc:.2f}). Sin cambios automáticos. Sensibilidad ajustada a {sensibilidad:.3f}, umbrales a {acc_bajo:.2f}/{acc_alto:.2f}.\nRecomendación: El sistema se mantiene estable, pero revisa periódicamente los logs y resultados.')
        except Exception as e:
            print(f'[MONITOREO] Error monitorizando accuracy: {e}')
        time.sleep(900)  # 15 minutos

if __name__ == "__main__":
    main()
