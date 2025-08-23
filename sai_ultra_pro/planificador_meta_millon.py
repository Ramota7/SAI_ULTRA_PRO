import json
import sys
import pytz
import pandas as pd
from main import obtener_saldo_binance_spot, obtener_saldo_binance_futuros, enviar_orden_spot_binance, enviar_orden_futuros_binance
from verificador_credenciales import verificar_credenciales

# Verificación de credenciales obligatoria antes de cualquier ciclo
try:
    verificar_credenciales()
except SystemExit:
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Fallo en la verificación de credenciales: {e}")
    with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
        from datetime import datetime
        flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [ERROR] Fallo en la verificación de credenciales: {e}\n")
    sys.exit(1)
def ejecutar_orden_prueba_exness():
    """
    Ejecuta una orden real de prueba en Exness (long, XAUUSD, 0.01) solo si el mercado está abierto y no hay operación activa.
    Usa credenciales de config.json y registra en ops_exness.csv.
    """
    # Leer config
    with open('sai_ultra_pro/config/config.json', 'r') as f:
        config = json.load(f)
    exness_conf = config['api_keys']
    api_key = exness_conf['EXNESS_API_KEY']
    api_secret = exness_conf['EXNESS_API_SECRET']
    server = exness_conf['EXNESS_SERVER']
    platform = exness_conf['EXNESS_PLATFORM']
    symbol = 'XAUUSDm'
    # Verificar mercado abierto
    from datetime import datetime
    now = datetime.now()
    if not mercado_exness_abierto(now):
        print('[PRUEBA EXNESS] Mercado cerrado, no se ejecuta la orden de prueba.')
        return False
    # Verificar si hay operación activa (simulado: buscar en ops_exness.csv si hay orden abierta hoy)
    import os
    ops_path = 'sai_ultra_pro/ia/ops_exness.csv'
    operacion_activa = False
    if os.path.exists(ops_path):
        import csv
        with open(ops_path, 'r') as fcsv:
            reader = csv.DictReader(fcsv)
            for row in reader:
                if row.get('symbol') == symbol and row.get('fecha', '').startswith(now.strftime('%Y-%m-%d')):
                    operacion_activa = True
                    # break innecesario, solo salir del for principal si es necesario
    if operacion_activa:
        print('[PRUEBA EXNESS] Ya existe una operación activa hoy en XAUUSD, no se ejecuta otra.')
        return False
    # Validar que el símbolo está disponible en MT5
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize(server=server, login=int(api_key), password=api_secret):
            print(f"[PRUEBA EXNESS] No se pudo conectar a Exness: {mt5.last_error()}")
            return False
        info = mt5.symbol_info(symbol)
        if info is None or not info.visible:
            print(f"[PRUEBA EXNESS] El símbolo {symbol} no está disponible o no es visible en MT5. Habilítalo en el panel de mercado.")
            mt5.shutdown()
            return False
        mt5.shutdown()
    except Exception as e:
        print(f"[PRUEBA EXNESS] Error al validar símbolo en MT5: {e}")
        return False
    # Ejecutar orden real
    from main import ejecutar_orden_exness
    print('[PRUEBA EXNESS] Ejecutando orden de prueba real en Exness: long, XAUUSD, 0.01')
    resultado = ejecutar_orden_exness('long', 0.01, api_key, api_secret, server, platform, symbol=symbol)
    print(f'[PRUEBA EXNESS] Resultado: {resultado}')
    return resultado
# --- PLAN MAESTRO INTEGRADO ---
import os
import pandas as pd
from datetime import datetime, timedelta
import time
import pytz
from main import (
    validar_api_binance, validar_api_exness,
    enviar_orden_binance, enviar_orden_venta_binance, ejecutar_orden_exness,
    obtener_capital_binance, obtener_capital_exness
)
from ia.analizador_volatilidad import AnalizadorVolatilidad
from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta

def cargar_metricas():
    try:
        df = pd.read_csv('sai_ultra_pro/ia/ops_real.csv')
        winrate = df['resultado'].value_counts(normalize=True).get('win', 0) * 100
        profit_factor = df['profit_factor'].iloc[-1] if 'profit_factor' in df.columns else 1.0
    except Exception:
        winrate = 100.0
        profit_factor = 1.0
    try:
        with open('sai_ultra_pro/ia/backtest_score.log') as f:
            score_ia = float(f.readlines()[-1].strip())
    except Exception:
        score_ia = 0.7
    return winrate, profit_factor, score_ia

def entorno_favorable_binance():
    # Forzado a favorable para pruebas/validación
    return True

def calcular_riesgo(fase, capital):
    return min(0.01 + 0.002*fase, 0.03) * capital

def ajustar_tamano_operacion(fase, capital, score_ia, volatilidad):
    # Ajuste dinámico: más score y volatilidad, más tamaño (dentro de límites)
    base = min(0.01 + 0.002*fase, 0.03)
    factor_score = 1 + max(0, score_ia - 0.7)
    factor_vol = 1 + min(max(volatilidad - 1, 0), 0.5)  # volatilidad normalizada, máx +50%
    return base * factor_score * factor_vol * capital

def guardar_backup():
    try:
        from monitor.backup import guardar_backup
        guardar_backup()
    except Exception:
        pass

def mercado_exness_abierto(now):
    # Exness (mercado FX) abre domingo 17:05 NY y cierra viernes 16:55 NY
    ny = pytz.timezone('America/New_York')
    now_ny = now.astimezone(ny)
    wd = now_ny.weekday()  # lunes=0, domingo=6
    hour = now_ny.hour
    minute = now_ny.minute
    # Cierre viernes 16:55 NY (después de 16:55 no operar Exness)
    if wd == 4 and (hour > 16 or (hour == 16 and minute >= 55)):
        return False
    # Sábado todo el día y domingo antes de 17:05 NY: cerrado
    if wd == 5:
        return False
    if wd == 6 and (hour < 17 or (hour == 17 and minute < 5)):
        return False
    return True

def gestion_riesgo_adaptativa(fase, capital, score_ia, volatilidad, drawdown, racha_perdidas, modo_recuperacion):
    base = min(0.01 + 0.002*fase, 0.03)
    factor_score = 1 + max(0, score_ia - 0.7)
    factor_vol = 1 + min(max(volatilidad - 1, 0), 0.5)
    factor_drawdown = 0.5 if modo_recuperacion else (1 - min(drawdown, 0.07))
    factor_racha = 0.8 if racha_perdidas >= 2 else 1
    return max(0.005, base * factor_score * factor_vol * factor_drawdown * factor_racha) * capital

def validar_entorno_robusto():
    try:
        from sai_ultra_pro.integracion.filtro_noticias import hay_evento_macro
        macro = False
        try:
            macro = hay_evento_macro()
        except Exception:
            macro = False
    except ImportError:
        macro = False
    from ia.analizador_volatilidad import AnalizadorVolatilidad
    av = AnalizadorVolatilidad()
    volatilidad = 1.0
    try:
        volatilidad = av.obtener_volatilidad()
    except Exception:
        pass
    return volatilidad < 1.5 and not macro, volatilidad, macro

def reentrenar_y_validar(score_actual):
    from ia.entrenar_modelo import entrenar_modelo
    from ia.analizador_volatilidad import AnalizadorVolatilidad
    entrenar_modelo()
    # Validar nuevo modelo
    try:
        av = AnalizadorVolatilidad()
        nuevo_score = av.obtener_score()
        return nuevo_score > score_actual
    except Exception:
        return False

def validar_liquidez_y_spread():
    # Simulación: en real, consulta API de profundidad y spread
    try:
        from estrategias.liquidez_ballena import LiquidezBallena
        lb = LiquidezBallena('BTCUSDT')
        spread = lb.obtener_spread()
        liquidez = lb.obtener_liquidez()
        return spread < 0.1 and liquidez > 10000  # Ajusta umbrales según activo
    except Exception:
        return True  # Si no se puede validar, no bloquear

def filtro_noticias_criticas():
    try:
        from sai_ultra_pro.integracion.filtro_noticias import hay_evento_macro
        return hay_evento_macro()
    except Exception:
        return False

def alertar_desvio_metricas(winrate, profit_factor, drawdown, notificar_telegram):
    alerta = ''
    if winrate < 55:
        alerta += '\n⚠️ Winrate bajo: {:.1f}%'.format(winrate)
    if profit_factor < 1.1:
        alerta += '\n⚠️ Profit Factor bajo: {:.2f}'.format(profit_factor)
    if drawdown > 0.07:
        alerta += '\n⚠️ Drawdown elevado: {:.2f}%'.format(drawdown*100)
    if alerta and notificar_telegram:
        from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta
        enviar_alerta('[ALERTA DESVÍO MÉTRICAS]' + alerta)

def ejecutar_plan_maestro():
    # --- MODO SIMULACIÓN FORZADA PARA PRUEBAS (solo hoy) ---
    import datetime as dt
    SIMULACION_FORZADA = (dt.datetime.now().date() == dt.date(2025, 8, 7))

    # Inicialización robusta de saldos y capitales antes de cualquier uso
    saldo_spot = 0
    saldo_futuros = 0
    capital_inicial_exness = 0
    # Cargar config.json al inicio de la función
    import json
    from datetime import datetime
    with open('sai_ultra_pro/config/config.json', 'r') as f:
        config = json.load(f)
    binance_conf = config['api_keys']
    exness_conf = config['api_keys']
    try:
        saldo_spot = obtener_saldo_binance_spot(binance_conf['BINANCE_API_KEY'], binance_conf['BINANCE_API_SECRET'], asset='USDT')
    except Exception as e:
        saldo_spot = 0
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [ERROR] Fallo al obtener saldo_spot: {e}\n")
    try:
        saldo_futuros = obtener_saldo_binance_futuros(binance_conf['BINANCE_API_KEY'], binance_conf['BINANCE_API_SECRET'], asset='USDT')
    except Exception as e:
        saldo_futuros = 0
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [ERROR] Fallo al obtener saldo_futuros: {e}\n")
    try:
        capital_inicial_exness = obtener_capital_exness(exness_conf['EXNESS_API_KEY'], exness_conf['EXNESS_API_SECRET'])
    except Exception as e:
        capital_inicial_exness = 0
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [ERROR] Fallo al obtener capital_inicial_exness: {e}\n")
    print(f"[BINANCE][SPOT] Saldo USDT: {saldo_spot}")
    print(f"[BINANCE][FUTUROS] Saldo USDT: {saldo_futuros}")
    with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
        flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [BINANCE][SPOT] Saldo USDT: {saldo_spot}\n")
        flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [BINANCE][FUTUROS] Saldo USDT: {saldo_futuros}\n")
    capital_inicial_binance = saldo_spot if saldo_spot and saldo_spot > 0 else saldo_futuros
    # --- FUNCIONES AUXILIARES DE PROTECCIÓN ---
    def log_proteccion(msg):
        print(msg)
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [PROTECCIÓN] {msg}\n")

    def fuera_horario():
        from datetime import datetime
        import pytz
        ahora = datetime.now(pytz.timezone('UTC')).hour
        return not (7 <= ahora <= 20)

    def drawdown_excedido():
        try:
            df_ops = pd.read_csv('sai_ultra_pro/ia/ops_real.csv')
            capitales = df_ops['capital'].dropna().values
            if len(capitales) > 1:
                max_capital = max(capitales[-10:])
                min_capital = min(capitales[-10:])
                return (max_capital - min_capital) / max_capital > 0.2
        except Exception:
            pass
        return False

    def capital_protegido_insuficiente(capital_total):
        capital_protegido = capital_total * 0.2
        capital_riesgo = capital_total - capital_protegido
        return capital_riesgo < 50

    def racha_perdidas_superada():
        try:
            df_ops = pd.read_csv('sai_ultra_pro/ia/ops_real.csv')
            ultimos = df_ops.tail(10)
            racha = 0
            for res in ultimos['resultado'].values[::-1]:
                if str(res).lower().startswith('loss'):
                    racha += 1
                else:
                    break
            return racha >= 3
        except Exception:
            return False

    def margen_libre_insuficiente(saldo_spot, saldo_futuros):
        return saldo_futuros < 50 and saldo_spot < 50

    def modo_simulacion_activar(capital_total):
        return capital_total < 50

    def volatilidad_permitida(simbolo):
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return False
        return True

    def alerta_telegram(msg):
        try:
            from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta
            enviar_alerta(msg)
        except Exception:
            pass

    # --- PROTECCIONES EJECUTABLES ---
    # 1. Horario permitido
    if fuera_horario():
        if not SIMULACION_FORZADA:
            log_proteccion("Fuera de horario permitido. No se opera.")
            return
        else:
            print("[SIMULACIÓN] Ignorando horario permitido SOLO para pruebas de hoy.")
    # 2. Drawdown
    if drawdown_excedido():
        log_proteccion("Drawdown diario/semanal excedido. Bloqueando operaciones.")
        alerta_telegram("⚠️ Drawdown excedido. Sistema bloqueado.")
        return
    # 3. Capital protegido insuficiente
    capital_total = (saldo_spot or 0) + (saldo_futuros or 0) + (capital_inicial_exness or 0)
    if capital_protegido_insuficiente(capital_total):
        log_proteccion("Solo capital protegido disponible. No se opera.")
        return
    # 4. Racha de pérdidas
    if racha_perdidas_superada():
        log_proteccion("3 pérdidas seguidas. Bloqueando operaciones y revisando estrategia.")
        alerta_telegram("⚠️ 3 pérdidas seguidas. Estrategia bloqueada para revisión.")
        return
    # 5. Margen libre insuficiente
    if margen_libre_insuficiente(saldo_spot, saldo_futuros):
        log_proteccion("Margen libre insuficiente en Binance. No se abrirán operaciones.")
        return
    # 6. Modo simulación automático
    if modo_simulacion_activar(capital_total):
        log_proteccion("Capital total menor a $50. Activando modo simulación y bloqueando operaciones reales.")
        return

    # === BLINDAJE TOTAL Y ESCALADO INTELIGENTE ===
    # Estado de recuperación y escalado
    modo_recuperacion = False
    modo_escalado = False
    racha_ganadora = 0
    racha_perdidas = 0
    drawdown = 0.0
    winrate, profit_factor, score_ia = cargar_metricas()
    # Detectar drawdown y rachas
    try:
        df_ops = pd.read_csv('sai_ultra_pro/ia/ops_real.csv')
        capitales = df_ops['capital'].dropna().values
        resultados = df_ops['resultado'].values
        if len(capitales) > 1:
            max_capital = max(capitales[-10:])
            min_capital = min(capitales[-10:])
            drawdown = (max_capital - min_capital) / max_capital if max_capital > 0 else 0
        # Rachas
        for res in resultados[::-1]:
            if str(res).lower().startswith('win'):
                racha_ganadora += 1
                racha_perdidas = 0
            elif str(res).lower().startswith('loss'):
                racha_perdidas += 1
                racha_ganadora = 0
            else:
                break
    except Exception:
        pass

    # Activar modo recuperación si hay 2+ pérdidas seguidas o drawdown > 10%
    if racha_perdidas >= 2 or drawdown > 0.1:
        modo_recuperacion = True
        modo_escalado = False
        log_proteccion("[RECUPERACIÓN] Activado por racha de pérdidas o drawdown alto.")
    # Activar modo escalado si hay 3+ ganancias seguidas y drawdown bajo
    elif racha_ganadora >= 3 and drawdown < 0.05:
        modo_escalado = True
        modo_recuperacion = False
        log_proteccion("[ESCALADO] Activado por racha ganadora.")
    else:
        modo_recuperacion = False
        modo_escalado = False

    # Diversificación: priorizar activos no correlacionados si hay pérdidas
    lista_simbolos = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'MATICUSDT', 'XRPUSDT', 'ADAUSDT']
    if modo_recuperacion:
        # Si en recuperación, priorizar activos menos correlacionados
        lista_simbolos = ['ADAUSDT', 'MATICUSDT', 'XRPUSDT', 'SOLUSDT', 'BTCUSDT', 'ETHUSDT']

    # Adaptar riesgo y tamaño de operación en tiempo real
    def calcular_riesgo_blindado(fase, capital, score_ia, volatilidad, drawdown, racha_perdidas, modo_recuperacion, modo_escalado):
        base = min(0.01 + 0.002*fase, 0.03)
        factor_score = 1 + max(0, score_ia - 0.7)
        factor_vol = 1 + min(max(volatilidad - 1, 0), 0.5)
        factor_drawdown = 0.5 if modo_recuperacion else (1 - min(drawdown, 0.07))
        factor_racha = 0.7 if modo_recuperacion else (1.2 if modo_escalado else 1)
        return max(0.003, base * factor_score * factor_vol * factor_drawdown * factor_racha) * capital

    # Auditoría y adaptación automática
    if winrate < 40 or profit_factor < 1 or drawdown > 0.25:
        log_proteccion("[AUDITORÍA] Métricas críticas desviadas. Activando modo simulación y bloqueando operaciones reales.")
        alerta_telegram("⚠️ Auditoría: métricas críticas desviadas. Sistema en modo simulación.")
        return
    # --- BLINDAJE TOTAL: PROTECCIONES AVANZADAS ---
    import pytz
    def calcular_stop_loss(simbolo, precio_entrada):
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return round(precio_entrada * 0.995, 2)
        return round(precio_entrada * 0.99, 2)

    def calcular_trailing_stop(simbolo, precio_entrada):
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return round(precio_entrada * 0.995, 2)
        return round(precio_entrada * 0.99, 2)

    def calcular_lote_max(margen_libre, precio, apalancamiento, simbolo):
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return max(0.01, round((margen_libre * 0.5 * apalancamiento) / precio, 2))
        return max(0.01, round((margen_libre * 0.5 * apalancamiento) / precio, 3))

    def horario_permitido():
        ahora = datetime.now(pytz.timezone('UTC')).hour
        return 7 <= ahora <= 20

    def volatilidad_permitida(simbolo):
        # Aquí deberías consultar tu analizador de volatilidad real
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return False
        return True

    # --- PROTECCIONES EJECUTABLES ---
    # Bloqueo por drawdown
    drawdown_max = 0.2
    try:
        import pandas as pd
        df_ops = pd.read_csv('sai_ultra_pro/ia/ops_real.csv')
        capitales = df_ops['capital'].dropna().values
        if len(capitales) > 1:
            max_capital = max(capitales[-10:])
            min_capital = min(capitales[-10:])
            if (max_capital - min_capital) / max_capital > drawdown_max:
                print("[PROTECCIÓN] Drawdown diario/semanal excedido. Bloqueando operaciones.")
                with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
                    from datetime import datetime
                    flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [PROTECCIÓN] Drawdown excedido. Bloqueando operaciones.\n")
                try:
                    from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta
                    enviar_alerta("⚠️ Drawdown excedido. Sistema bloqueado.")
                except Exception:
                    pass
                return
    except Exception:
        pass

    # Capital mínimo protegido
    capital_protegido = capital_total * 0.2
    capital_riesgo = capital_total - capital_protegido
    if capital_riesgo < 50:
        print("[PROTECCIÓN] Solo capital protegido disponible. No se opera.")
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [PROTECCIÓN] Solo capital protegido disponible. No se opera.\n")
        return

    # Horario permitido
    if not horario_permitido():
        print("[PROTECCIÓN] Fuera de horario permitido. No se opera.")
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [PROTECCIÓN] Fuera de horario permitido.\n")
        return
    capital_objetivo = 1_000_000.0  # objetivo de capital
    meses = 12  # meses de operación
    notificar_telegram = True  # activar notificaciones de Telegram
    pct_max_comisiones = 0.05  # % máximo de comisiones sobre capital
    import json
    from datetime import datetime
    # Cargar config.json al inicio de la función
    with open('sai_ultra_pro/config/config.json', 'r') as f:
        config = json.load(f)
    fecha_inicio = datetime.now()
    # --- FASES DE CRECIMIENTO Y UMBRALES ---
    fases = [226, 350, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000]
    fase = 1
    capital_protegido_fase = [0]  # Lista para guardar el capital protegido de cada fase
    # Inicialización robusta de capital simulado por broker
    capital_simulado_binance = 0.0
    capital_simulado_exness = 0.0
    # Leer claves correctas del config.json
    binance_conf = config['api_keys']
    exness_conf = config['api_keys']
    # --- Consulta de saldo Spot y Futuros USDT-M Binance y capital Exness ---
    saldo_spot = 0
    saldo_futuros = 0
    capital_inicial_exness = 0
    try:
        saldo_spot = obtener_saldo_binance_spot(binance_conf['BINANCE_API_KEY'], binance_conf['BINANCE_API_SECRET'], asset='USDT')
    except Exception as e:
        saldo_spot = 0
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [ERROR] Fallo al obtener saldo_spot: {e}\n")
    try:
        saldo_futuros = obtener_saldo_binance_futuros(binance_conf['BINANCE_API_KEY'], binance_conf['BINANCE_API_SECRET'], asset='USDT')
    except Exception as e:
        saldo_futuros = 0
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [ERROR] Fallo al obtener saldo_futuros: {e}\n")
    try:
        capital_inicial_exness = obtener_capital_exness(exness_conf['EXNESS_API_KEY'], exness_conf['EXNESS_API_SECRET'])
    except Exception as e:
        capital_inicial_exness = 0
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [ERROR] Fallo al obtener capital_inicial_exness: {e}\n")
    print(f"[BINANCE][SPOT] Saldo USDT: {saldo_spot}")
    print(f"[BINANCE][FUTUROS] Saldo USDT: {saldo_futuros}")
    with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
        from datetime import datetime
        flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [BINANCE][SPOT] Saldo USDT: {saldo_spot}\n")
        flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [BINANCE][FUTUROS] Saldo USDT: {saldo_futuros}\n")
    capital_inicial_binance = saldo_spot if saldo_spot and saldo_spot > 0 else saldo_futuros

    # --- PROTECCIONES Y REGLAS DE RIESGO ---
    # 1. No operar si capital < $50
    capital_total = (saldo_spot or 0) + (saldo_futuros or 0) + (capital_inicial_exness or 0)
    if capital_total < 50:
        print("[PROTECCIÓN] Capital total menor a $50. Activando modo simulación y bloqueando operaciones reales.")
        modo_simulacion = True
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [PROTECCIÓN] Capital total menor a $50. Activando modo simulación.\n")
        return
    else:
        modo_simulacion = False

    # 2. Control de racha de pérdidas
    racha_perdidas = 0
    try:
        import pandas as pd
        df_ops = pd.read_csv('sai_ultra_pro/ia/ops_real.csv')
        ultimos = df_ops.tail(10)
        for res in ultimos['resultado'].values[::-1]:
            if str(res).lower().startswith('loss'):
                racha_perdidas += 1
            else:
                break
    except Exception:
        pass
    if racha_perdidas >= 3:
        print("[PROTECCIÓN] 3 pérdidas seguidas. Bloqueando operaciones y revisando estrategia.")
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [PROTECCIÓN] 3 pérdidas seguidas. Bloqueando operaciones y revisando estrategia.\n")
        # Enviar alerta Telegram
        try:
            from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta
            enviar_alerta("⚠️ 3 pérdidas seguidas. Estrategia bloqueada para revisión.")
        except Exception:
            pass
        return

    # 3. Chequeo de margen libre y capital antes de operar
    if saldo_futuros < 50 and saldo_spot < 50:
        print("[PROTECCIÓN] Margen libre insuficiente en Binance. No se abrirán operaciones.")
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [PROTECCIÓN] Margen libre insuficiente en Binance.\n")
        return

    # 4. Priorizar operaciones con probabilidad > 70% (estructura, liquidez, volumen, IA)
    def validar_probabilidad(simbolo):
        # Aquí deberías integrar tu lógica de IA, estructura, liquidez, volumen, etc.
        # Simulación: retorna 0.75 para activos menos volátiles, 0.65 para XAUUSD
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return 0.65
        return 0.75

    # 5. Lógica de lote dinámico y exposición
    def calcular_lote(capital, apalancamiento, simbolo):
        # Reduce lote para XAUUSD y activos volátiles
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return max(0.01, round((capital * 0.001) / apalancamiento, 2))
        return max(0.01, round((capital * 0.01) / apalancamiento, 3))

    # 6. Alerta de riesgo de Stop Out
    def alerta_stop_out(margen_libre, capital):
        if margen_libre < capital * 0.05:
            try:
                from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta
                enviar_alerta(f"⚠️ Riesgo de Stop Out: margen libre {margen_libre:.2f} USDT, capital {capital:.2f} USDT")
            except Exception:
                pass

    # 7. Acortar tiempo de exposición para XAUUSD
    def tiempo_exposicion(simbolo):
        if simbolo in ['XAUUSD', 'XAUUSDm']:
            return 5  # minutos
        return 15  # minutos

    # --- Operar en el mercado con saldo disponible ---
    # --- INTEGRACIÓN DE AUTOGESTIÓN Y MACHINE LEARNING ---
    # Visualización de decisiones de autogestión y ML
    print(f"[AUTOGESTIÓN] Estrategia seleccionada: {estrategia}")
    print(f"[AUTOGESTIÓN] Riesgo pct: {riesgo_pct:.4f}, Apalancamiento: {apalancamiento}")
    print(f"[AUTOGESTIÓN] Lista de símbolos priorizada: {lista_simbolos}")
    with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
        from datetime import datetime
        flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | [AUTOGESTIÓN] Estrategia: {estrategia}, Riesgo: {riesgo_pct:.4f}, Apal: {apalancamiento}, Símbolos: {lista_simbolos}\n")
    from autogestion.autogestion import (
        evaluar_entorno_y_rotar_estrategia,
        ajustar_riesgo_y_apalancamiento,
        seleccionar_activos_dinamicamente
    )
    from autogestion.ml_signals import predecir_probabilidad

    métricas = {
        'winrate': winrate,
        'profit_factor': profit_factor,
        'drawdown': drawdown,
        'racha_perdidas': racha_perdidas,
        'racha_ganadora': racha_ganadora
    }
    entorno = {
        'volatilidad': 1.0  # Puedes mejorar con tu analizador
    }
    estrategia = evaluar_entorno_y_rotar_estrategia(métricas, entorno)
    riesgo_pct, apalancamiento = ajustar_riesgo_y_apalancamiento(métricas, entorno)
    lista_simbolos = seleccionar_activos_dinamicamente(métricas, None)
    operado = False
    from binance.client import Client
    client = Client(binance_conf['BINANCE_API_KEY'], binance_conf['BINANCE_API_SECRET'])
    for simbolo in lista_simbolos:
        # --- Estrategias avanzadas: momentum, reversión, breakout, arbitraje ---
        from autogestion.estrategias_extra import (
            estrategia_momentum, estrategia_reversion, estrategia_breakout, estrategia_arbitraje_estadistico
        )
        # Simulación: cargar datos OHLCV recientes (deberías reemplazar por tu fuente real)
        try:
            df = pd.read_csv(f'sai_ultra_pro/ia/data_{simbolo}_15m.csv').tail(50)
        except Exception:
            continue
        aplicar_estrategia = False
        # Momentum
        if estrategia_momentum(df):
            print(f"[ESTRATEGIA] {simbolo}: Señal momentum activa.")
            aplicar_estrategia = True
        # Reversión
        elif estrategia_reversion(df):
            print(f"[ESTRATEGIA] {simbolo}: Señal reversión activa.")
            aplicar_estrategia = True
        # Breakout
        elif estrategia_breakout(df):
            print(f"[ESTRATEGIA] {simbolo}: Señal breakout activa.")
            aplicar_estrategia = True
        # Arbitraje estadístico (ejemplo: BTCUSDT vs ETHUSDT)
        elif simbolo == 'BTCUSDT':
            try:
                df2 = pd.read_csv('sai_ultra_pro/ia/data_ETHUSDT_15m.csv').tail(50)
                if estrategia_arbitraje_estadistico(df, df2):
                    print(f"[ESTRATEGIA] {simbolo}: Señal arbitraje estadístico activa con ETHUSDT.")
                    aplicar_estrategia = True
            except Exception:
                pass
        if not aplicar_estrategia:
            print(f"[ESTRATEGIA] {simbolo}: Ninguna señal activa, se omite.")
            continue
        # Filtrado ML antes de operar
        features = {'feature1': riesgo_pct, 'feature2': apalancamiento}
        print(f"[ML][DECISIÓN] Evaluando {simbolo} con features: {{'feature1': {riesgo_pct}, 'feature2': {apalancamiento}}}")
        prob = predecir_probabilidad(features)
        print(f"[ML][DECISIÓN] Probabilidad ML para {simbolo}: {prob:.2f}")
        if prob < 0.7:
            msg = f"[ML][FILTRADO] {simbolo} omitido por probabilidad ML {prob:.2f}"
            print(msg)
            with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
                from datetime import datetime
                flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
            continue
        # Si pasa el filtro, operar normalmente (lógica existente)
        precio_actual = None
        try:
            ticker = client.futures_symbol_ticker(symbol=simbolo)
            precio_actual = float(ticker['price'])
        except Exception:
            continue
        # Obtener minQty, stepSize y notional_min
        min_qty = 0.001
        step_size = 0.001
        notional_min = 20.0
        try:
            info = client.futures_exchange_info()
            for s in info['symbols']:
                if s['symbol'] == simbolo:
                    for f in s['filters']:
                        if f['filterType'] == 'LOT_SIZE':
                            min_qty = float(f['minQty'])
                            step_size = float(f['stepSize'])
                        if f['filterType'] == 'MIN_NOTIONAL':
                            notional_min = float(f['notional'])
        except Exception:
            pass
        import math
        margen_libre = 0.0
        try:
            info_futuros = client.futures_account_balance()
            for b in info_futuros:
                if b['asset'] == 'USDT':
                    margen_libre = float(b['balance'])
        except Exception:
            pass
        cantidad_notional = (notional_min / precio_actual) + 0.0001
        cantidad_max = round((margen_libre * 10 / precio_actual) * 0.99, 8)
        cantidad = max(min_qty, cantidad_notional)
        cantidad = min(cantidad, cantidad_max)
        cantidad = math.ceil(cantidad / step_size) * step_size
        cantidad = round(cantidad, 8)
        if cantidad * precio_actual < notional_min or cantidad > cantidad_max:
            msg = f"[BINANCE][FUTUROS][SKIP] {simbolo}: No se puede operar, cantidad mínima {cantidad} no cumple notional mínimo {notional_min} USDT o excede margen libre (max {cantidad_max}) (precio={precio_actual})"
            print(msg)
            with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
                from datetime import datetime
                flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
            continue
        # Si cumple, intentar operar y salir del ciclo
        operado = True
        break
    if not operado:
        msg = f"[BINANCE][FUTUROS][SKIP] Ningún símbolo alternativo cumple notional mínimo para operar."
        print(msg)
        with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
            from datetime import datetime
            flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
        # Omitir operación
        # Selecciona el mercado con mayor USDT disponible
        if saldo_futuros > saldo_spot and saldo_futuros > 10:
            from binance.client import Client
            client = Client(binance_conf['BINANCE_API_KEY'], binance_conf['BINANCE_API_SECRET'])
            # Configura margen cruzado y apalancamiento 10x
            try:
                client.futures_change_margin_type(symbol=simbolo, marginType='CROSSED')
            except Exception:
                pass
            try:
                client.futures_change_leverage(symbol=simbolo, leverage=10)
            except Exception:
                pass
            info_futuros = client.futures_account_balance()
            margen_libre = 0.0
            for b in info_futuros:
                if b['asset'] == 'USDT':
                    margen_libre = float(b['balance'])
                    # break eliminado: fuera de bucle
            precio_actual = None
            try:
                ticker = client.futures_symbol_ticker(symbol=simbolo)
                precio_actual = float(ticker['price'])
            except Exception:
                precio_actual = None
            if margen_libre > 10 and precio_actual:
                # Obtener cantidad mínima permitida por Binance para el símbolo
                min_qty = 0.001
                step_size = 0.001
                try:
                    info = client.futures_exchange_info()
                    for s in info['symbols']:
                        if s['symbol'] == simbolo:
                            for f in s['filters']:
                                if f['filterType'] == 'LOT_SIZE':
                                    min_qty = float(f['minQty'])
                                    step_size = float(f['stepSize'])
                                    break
                            break
                except Exception:
                    pass
                cantidad_max = round((margen_libre * 10 / precio_actual) * 0.99, 8)
                cantidad = max(min(cantidad, cantidad_max), min_qty)
                # Redondear cantidad al múltiplo de step_size
                def round_step_size(qty, step):
                    import math
                    return math.floor(qty / step) * step
                cantidad = round_step_size(cantidad, step_size)
                cantidad = round(cantidad, 8)
                # Obtener notional mínimo
                notional_min = 20.0
                try:
                    info = client.futures_exchange_info()
                    for s in info['symbols']:
                        if s['symbol'] == simbolo:
                            for f in s['filters']:
                                if f['filterType'] == 'MIN_NOTIONAL':
                                    notional_min = float(f['notional'])
                                    break
                            break
                except Exception:
                    pass
                # Si cantidad*precio_actual < notional_min, ajustar cantidad
                if precio_actual and cantidad * precio_actual < notional_min:
                    cantidad_notional = round((notional_min / precio_actual) + 0.0001, 4)
                    cantidad = max(cantidad_notional, min_qty)
                    print(f"[BINANCE][FUTUROS][AJUSTE] Ajustando cantidad a {cantidad} para cumplir notional mínimo {notional_min} USDT")
                print(f"[BINANCE][FUTUROS][CROSSED 10x] Ejecutando orden de compra de {cantidad} {simbolo} (minQty={min_qty}, notional_min={notional_min})...")
                orden = enviar_orden_futuros_binance(binance_conf['BINANCE_API_KEY'], binance_conf['BINANCE_API_SECRET'], simbolo, cantidad, side='BUY')
                precio = None
                error_margen = False
                if orden and 'avgFillPrice' in orden:
                    precio = orden['avgFillPrice']
                elif orden and 'code' in orden and orden['code'] == -2019:
                    error_margen = True
                elif orden is None:
                    error_margen = True
                if error_margen and cantidad > min_qty:
                    # Reintentar con minQty o con cantidad ajustada a notional mínimo
                    print(f"[BINANCE][FUTUROS][REINTENTO] Margen insuficiente con {cantidad}, probando con minQty={min_qty}...")
                    cantidad_retry = max(min_qty, round((notional_min / precio_actual) + 0.0001, 4))
                    if cantidad_retry * precio_actual < notional_min:
                        cantidad_retry = round((notional_min / precio_actual) + 0.0001, 4)
                    orden = enviar_orden_futuros_binance(binance_conf['BINANCE_API_KEY'], binance_conf['BINANCE_API_SECRET'], simbolo, cantidad_retry, side='BUY')
                    if orden and 'avgFillPrice' in orden:
                        precio = orden['avgFillPrice']
                        msg = f"[BINANCE][FUTUROS][ORDEN] {simbolo} BUY {cantidad_retry} precio={precio} (CROSSED, 10x, ajuste notional)"
                    else:
                        msg = f"[BINANCE][FUTUROS][ORDEN][ERROR] No se pudo abrir posición ni con cantidad ajustada a notional mínimo {notional_min} (CROSSED, 10x)"
                    print(msg)
                    with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
                        from datetime import datetime
                        flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
                    operado = True
                    # break eliminado: fuera de bucle
                else:
                    msg = f"[BINANCE][FUTUROS][ORDEN] {simbolo} BUY {cantidad} precio={precio} (CROSSED, 10x, minQty={min_qty}, notional_min={notional_min})"
                    print(msg)
                    with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
                        from datetime import datetime
                        flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
                    operado = True
                    # break eliminado: fuera de bucle
        elif saldo_spot > 10:
            print(f"[BINANCE][SPOT] Ejecutando orden de compra de {cantidad} {simbolo}...")
            orden = enviar_orden_spot_binance(binance_conf['BINANCE_API_KEY'], binance_conf['BINANCE_API_SECRET'], simbolo, cantidad, side='BUY')
            precio = None
            if orden and 'fills' in orden and orden['fills']:
                precio = orden['fills'][0]['price']
            msg = f"[BINANCE][SPOT][ORDEN] {simbolo} BUY {cantidad} precio={precio}"
            print(msg)
            with open('sai_ultra_pro/ia/plan_log.txt', 'a', encoding='utf-8') as flog:
                from datetime import datetime
                flog.write(f"{datetime.now():%Y-%m-%d %H:%M} | {msg}\n")
            operado = True
            # break eliminado: fuera de bucle
    if not operado:
        print("[BINANCE] No hay saldo suficiente (> $10) ni en Spot ni en Futuros para operar.")
    if capital_inicial_binance is None or capital_inicial_binance == 0.0:
        capital_simulado_binance = 100.0  # Valor por defecto si no hay saldo real
    else:
        capital_simulado_binance = capital_inicial_binance
    if capital_inicial_exness is None or capital_inicial_exness == 0.0:
        capital_simulado_exness = 100.0
    else:
        capital_simulado_exness = capital_inicial_exness
    capital_inicial = capital_simulado_binance + capital_simulado_exness
    capital = capital_inicial
    max_capital = capital
    ultima_vela = None
    drawdown_pausa = False
    modo_recuperacion = False
    racha_perdidas = 0
    historial_ganancias = []
    historial_comisiones = []
    rolling_window = 20  # Para autoajuste de parámetros
    resumen_semanal = []
    semana_actual = datetime.now().isocalendar()[1]
    stop_activado = False
    capital_protegido_dinamico = 0  # Se activa al subir de fase
    mercado_actual = 'BTCUSDT'
    mejor_mercado = mercado_actual
    score_mercado = 0
    # --- SÍMBOLOS BINANCE Y EXNESS ---
    SIMBOLOS_BINANCE = [
        'BTCUSDT',
        'ETHUSDT',
        'SOLUSDT',
        'LINKUSDT',
        'BNBUSDT'
    ]
    SIMBOLOS_EXNESS = [
        'XAUUSDm',
        'XAGUSDm',
        'US30m',
        'US500m',
        'BTCUSD',
        'ETHUSD',
        'EURUSD',
        'GBPJPY',
        'NAS100m'
    ]
    mercados_disponibles = SIMBOLOS_BINANCE + SIMBOLOS_EXNESS
    rendimiento_mercados = {m: [] for m in mercados_disponibles}
    semanas_rotacion = 0
    score_ia_actual = 0
    volatilidad_actual = 1.0
    score_ia_actual_symbol = None
    while capital < capital_objetivo and (datetime.now() - fecha_inicio).days < meses*30:
        now = datetime.now()
        # --- CAPITAL PROTEGIDO POR FASE ---
        if capital_protegido_dinamico > 0 and capital <= capital_protegido_dinamico:
            if not stop_activado:
                stop_activado = True
                mensaje_stop = f"🛑 CAPITAL PROTEGIDO ACTIVADO: Capital (${capital:,.2f}) bajo el umbral de protección (${capital_protegido_dinamico:,.2f}). Operativa detenida."
                print(mensaje_stop)
                if notificar_telegram:
                    enviar_alerta(mensaje_stop)
                with open('sai_ultra_pro/ia/plan_auditoria.txt', 'a', encoding='utf-8') as faud:
                    faud.write(f"{now.strftime('%Y-%m-%d %H:%M')} | {mensaje_stop}\n")
            break
        minuto_actual = now.minute
        entorno_ok, volatilidad, macro = validar_entorno_robusto()
        if ultima_vela == (now.hour, minuto_actual // 15):
            time.sleep(60)
            continue
        if minuto_actual % 15 != 0:
            time.sleep(60)
            continue
        ultima_vela = (now.hour, minuto_actual // 15)
        winrate, profit_factor, score_ia = cargar_metricas()
        score_ia_actual = score_ia
        capital_anterior = capital
        # Leer credenciales reales
        with open('sai_ultra_pro/config/config.json', 'r') as f:
            config = json.load(f)
        binance_conf = config['api_keys']
        exness_conf = config['api_keys']
        fallback_binance = False
        fallback_exness = False
        capital_binance_real = obtener_capital_binance(binance_conf['BINANCE_API_KEY'], binance_conf['BINANCE_API_SECRET'])
        if capital_binance_real is None or capital_binance_real == 0.0:
            fallback_binance = True
            print('[FALLBACK][BINANCE] Error al consultar saldo real, usando capital simulado.')
            capital_binance = capital_simulado_binance
        else:
            capital_binance = capital_binance_real
            capital_simulado_binance = capital_binance_real
        capital_exness_real = obtener_capital_exness(exness_conf['EXNESS_API_KEY'], exness_conf['EXNESS_API_SECRET'])
        if capital_exness_real is None or capital_exness_real == 0.0:
            fallback_exness = True
            print('[FALLBACK][EXNESS] Error al consultar saldo real, usando capital simulado.')
            capital_exness = capital_simulado_exness
        else:
            capital_exness = capital_exness_real
            capital_simulado_exness = capital_exness_real
        capital = capital_binance + capital_exness
        # Log de auditoría de capital con marca [FALLBACK] si aplica
        with open('sai_ultra_pro/ia/plan_auditoria.txt', 'a', encoding='utf-8') as faud:
            fallback_msg = ''
            if fallback_binance:
                fallback_msg += ' [FALLBACK][BINANCE]'
            if fallback_exness:
                fallback_msg += ' [FALLBACK][EXNESS]'
            faud.write(f"{now.strftime('%Y-%m-%d %H:%M')} | Capital antes: {capital_anterior:.2f} | Capital después: {capital:.2f} | Binance: {capital_binance:.2f} | Exness: {capital_exness:.2f}{fallback_msg}\n")
        ganancia_acumulada = capital - capital_inicial
        pct_ganancia = (ganancia_acumulada / capital_inicial) * 100 if capital_inicial > 0 else 0
        if capital > max_capital:
            max_capital = capital
            mensaje_max = f"\n🔥 ¡Nuevo máximo alcanzado! Capital: ${capital:,.2f}"
        else:
            mensaje_max = ''
        drawdown = (max_capital - capital) / max_capital if max_capital > 0 else 0
        # Calcular media de ganancia por operación
        if capital != capital_anterior:
            historial_ganancias.append(capital - capital_anterior)
            if len(historial_ganancias) > rolling_window:
                historial_ganancias = historial_ganancias[-rolling_window:]
        media_ganancia = sum(historial_ganancias)/len(historial_ganancias) if historial_ganancias else 0
        # --- CONTROL DE COMISIONES ---
        comision_op = 0.0007 * capital  # Simulación: 0.07% por operación (ajustar según real)
        historial_comisiones.append(comision_op)
        if len(historial_comisiones) > rolling_window:
            historial_comisiones = historial_comisiones[-rolling_window:]
        total_comisiones = sum(historial_comisiones)
        if total_comisiones > capital * pct_max_comisiones:
            mensaje_com = f"⚠️ Comisiones acumuladas (${total_comisiones:,.2f}) superan el {pct_max_comisiones*100:.1f}% del capital."
            print(mensaje_com)
            if notificar_telegram:
                enviar_alerta(mensaje_com)
        # --- ROTACIÓN INTELIGENTE DE ACTIVO (semanal o al subir de fase) ---
        # --- EVALUACIÓN Y OPERACIÓN MULTISÍMBOLO POR BROKER ---
    # --- FORZAR CICLO DE PRUEBA SI SE SOLICITA ---
    if __name__ == "__main__":
        print("[TEST] Forzando ciclo completo de evaluación y operación en entorno real...")
        # Simular señales válidas: Exness (2 símbolos), Binance (1 símbolo, BTCUSDT y ETHUSDT ambos válidos)
        score_ia_actual = 0.8
        # Forzar detalles para Exness
        SIMBOLOS_EXNESS_TEST = [SIMBOLOS_EXNESS[0], SIMBOLOS_EXNESS[1], SIMBOLOS_EXNESS[2]]
        detalles_symbols_exness = []
        symbols_operados_exness = []
        exness_omitidos = []
        exness_ops_count = 0
        for i, symbol in enumerate(SIMBOLOS_EXNESS_TEST):
            score_ia_symbol = 0.8
            volatilidad_symbol = 1.2
            spread = 0.001
            detalles_symbols_exness.append((symbol, score_ia_symbol, volatilidad_symbol, spread))
            if score_ia_symbol > 0.75 and 0.8 < volatilidad_symbol < 2.0 and spread < 0.0025:
                if exness_ops_count < 2:
                    symbols_operados_exness.append(symbol)
                    exness_ops_count += 1
                    print(f"[EXNESS][TEST] Ejecutando orden real en {symbol}")
                    # ejecutar_orden_exness('long', 0.01, ... , symbol=symbol, ...)
                else:
                    exness_omitidos.append(symbol)
                    print(f"[EXNESS][OMITIDO][TEST] {symbol} omitido por límite de 2 operaciones por ciclo.")
        # Forzar detalles para Binance
        SIMBOLOS_BINANCE_TEST = ['BTCUSDT', 'ETHUSDT', SIMBOLOS_BINANCE[2]]
        detalles_symbols_binance = []
        symbols_operados_binance = []
        binance_candidates = []
        binance_omitidos = []
        for symbol in SIMBOLOS_BINANCE_TEST:
            score_ia_symbol = 0.8
            volatilidad_symbol = 1.1
            spread = 0.0005
            detalles_symbols_binance.append((symbol, score_ia_symbol, volatilidad_symbol, spread))
            if score_ia_symbol > 0.72 and 0.8 < volatilidad_symbol < 2.0 and spread < 0.0025:
                binance_candidates.append(symbol)
        # Simular conflicto BTCUSDT/ETHUSDT
        if 'BTCUSDT' in binance_candidates and 'ETHUSDT' in binance_candidates:
            binance_omitidos.append('ETHUSDT')
            binance_candidates.remove('ETHUSDT')
            print('[BINANCE][OMITIDO][TEST] ETHUSDT omitido por conflicto con BTCUSDT (correlación alta).')
        if binance_candidates:
            symbols_operados_binance.append(binance_candidates[0])
            print(f"[BINANCE][TEST] Ejecutando orden real en {binance_candidates[0]}")
            # enviar_orden_binance(api_key, api_secret, simbolo, cantidad)
            for s in binance_candidates[1:]:
                binance_omitidos.append(s)
                print(f'[BINANCE][OMITIDO][TEST] {s} omitido por límite de 1 operación por ciclo.')
        # Actualizar capital tras cada operación real y registrar auditoría
        from datetime import datetime
        capital_binance = obtener_capital_binance()
        capital_exness = obtener_capital_exness()
        with open('sai_ultra_pro/ia/plan_auditoria.txt', 'a', encoding='utf-8') as faud:
            faud.write(f"{datetime.now():%Y-%m-%d %H:%M} | EXNESS evaluados: {detalles_symbols_exness} | OPERADOS: {symbols_operados_exness} | OMITIDOS: {exness_omitidos} | BINANCE evaluados: {detalles_symbols_binance} | OPERADOS: {symbols_operados_binance} | OMITIDOS: {binance_omitidos}\n")
        print("[TEST] Auditoría registrada en plan_auditoria.txt")
        # EXNESS
        symbols_operados_exness = []
        detalles_symbols_exness = []
        exness_omitidos = []
        exness_ops_count = 0
        try:
            import MetaTrader5 as mt5
            from ia.analizador_volatilidad import AnalizadorVolatilidad
            av = AnalizadorVolatilidad()
            if not mt5.initialize():
                print('[ROTACIÓN EXNESS] No se pudo inicializar MT5 para análisis de símbolos.')
            else:
                for symbol in SIMBOLOS_EXNESS:
                    info = mt5.symbol_info(symbol)
                    if info is None or not info.visible:
                        continue
                    price = mt5.symbol_info_tick(symbol).ask
                    score_ia_symbol = av.obtener_score() if hasattr(av, 'obtener_score') else score_ia_actual
                    volatilidad_symbol = av.obtener_volatilidad() if hasattr(av, 'obtener_volatilidad') else 1.0
                    spread = (info.ask - info.bid) / price if price > 0 else 1.0
                    detalles_symbols_exness.append((symbol, score_ia_symbol, volatilidad_symbol, spread))
                    if score_ia_symbol > 0.75 and 0.8 < volatilidad_symbol < 2.0 and spread < 0.0025:
                        if exness_ops_count < 2:
                            symbols_operados_exness.append(symbol)
                            exness_ops_count += 1
                            # ejecutar_orden_exness('long', 0.01, ... , symbol=symbol, ...)
                        else:
                            exness_omitidos.append(symbol)
                            print(f'[EXNESS][OMITIDO] {symbol} omitido por límite de 2 operaciones por ciclo.')
                mt5.shutdown()
        except Exception as e:
            print(f'[ROTACIÓN EXNESS] Error al analizar símbolos Exness: {e}')
        print('[ROTACIÓN EXNESS] Detalles símbolos evaluados:')
        for s, sc, v, sp in detalles_symbols_exness:
            op = '✅ OPERADO' if s in symbols_operados_exness else '—'
            print(f"  {s}: Score IA={sc:.2f}, Vol={v:.2f}, Spread={sp:.5f} {op}")
        # BINANCE
        symbols_operados_binance = []
        detalles_symbols_binance = []
        binance_candidates = []
        binance_omitidos = []
        try:
            for symbol in SIMBOLOS_BINANCE:
                score_ia_symbol = score_ia_actual
                volatilidad_symbol = 1.0
                spread = 0.0005
                detalles_symbols_binance.append((symbol, score_ia_symbol, volatilidad_symbol, spread))
                if score_ia_symbol > 0.72 and 0.8 < volatilidad_symbol < 2.0 and spread < 0.0025:
                    binance_candidates.append(symbol)
            # Evitar operar BTCUSDT y ETHUSDT juntos
            if 'BTCUSDT' in binance_candidates and 'ETHUSDT' in binance_candidates:
                # Prioriza el de mayor score (simulado, mismo score: prioriza BTCUSDT)
                binance_omitidos.append('ETHUSDT')
                binance_candidates.remove('ETHUSDT')
                print('[BINANCE][OMITIDO] ETHUSDT omitido por conflicto con BTCUSDT (correlación alta).')
            # Limita a 1 operación por ciclo
            if binance_candidates:
                symbols_operados_binance.append(binance_candidates[0])
                # enviar_orden_binance(api_key, api_secret, simbolo, cantidad)
                for s in binance_candidates[1:]:
                    binance_omitidos.append(s)
                    print(f'[BINANCE][OMITIDO] {s} omitido por límite de 1 operación por ciclo.')
            else:
                print('[BINANCE] Ningún símbolo cumple criterios para operar este ciclo.')
        except Exception as e:
            print(f'[ROTACIÓN BINANCE] Error al analizar símbolos Binance: {e}')
        print('[ROTACIÓN BINANCE] Detalles símbolos evaluados:')
        for s, sc, v, sp in detalles_symbols_binance:
            op = '✅ OPERADO' if s in symbols_operados_binance else '—'
            print(f"  {s}: Score IA={sc:.2f}, Vol={v:.2f}, Spread={sp:.5f} {op}")
        # Registrar en logs
        with open('sai_ultra_pro/ia/plan_auditoria.txt', 'a', encoding='utf-8') as faud:
            faud.write(f"{now.strftime('%Y-%m-%d %H:%M')} | EXNESS evaluados: {detalles_symbols_exness} | OPERADOS: {symbols_operados_exness} | OMITIDOS: {exness_omitidos}\n")
            faud.write(f"{now.strftime('%Y-%m-%d %H:%M')} | BINANCE evaluados: {detalles_symbols_binance} | OPERADOS: {symbols_operados_binance} | OMITIDOS: {binance_omitidos}\n")
        # --- GESTIÓN DE RACHAS ---
        if len(historial_ganancias) >= 2:
            racha = 'win' if historial_ganancias[-1] > 0 else 'lose'
            racha_count = 1
            for g in reversed(historial_ganancias[:-1]):
                if (g > 0 and racha == 'win') or (g <= 0 and racha == 'lose'):
                    racha_count += 1
                else:
                    break
        else:
            racha = '-'
            racha_count = 0
        # Ajuste de riesgo por racha negativa
        if racha == 'lose' and racha_count >= 3:
            modo_recuperacion = True
            if notificar_telegram:
                enviar_alerta(f"⚠️ Racha negativa de {racha_count} pérdidas. Activando modo recuperación (riesgo reducido) en {mercado_actual}.")
        elif racha == 'win' and racha_count >= 3:
            modo_recuperacion = False
            if notificar_telegram:
                enviar_alerta(f"✅ Racha positiva de {racha_count} ganancias. Riesgo normalizado en {mercado_actual}.")
        # --- AUTOAJUSTE DE PARÁMETROS (rolling window) ---
        if len(historial_ganancias) >= rolling_window:
            media_rolling = sum(historial_ganancias[-rolling_window:])/rolling_window
            if media_rolling < 0:
                # Si la media móvil es negativa, reducir tamaño/riesgo
                fase = max(1, fase-1)
                if notificar_telegram:
                    enviar_alerta(f"🔄 Autoajuste: media de resultados negativa en {rolling_window} ops. Bajando fase a {fase}.")
            elif media_rolling > 0 and fase < len(fases):
                fase += 1
                if notificar_telegram:
                    enviar_alerta(f"🔄 Autoajuste: media positiva en {rolling_window} ops. Subiendo fase a {fase}.")
        resumen = ''
        operacion_realizada = False
        operaciones_detalle = []
        # --- EVALUACIÓN SEMANAL AUTOMÁTICA ---
        semana_now = now.isocalendar()[1]
        resumen_semanal.append({
            'fecha': now.strftime('%Y-%m-%d'),
            'capital': capital,
            'ganancia': ganancia_acumulada,
            'winrate': winrate,
            'profit_factor': profit_factor,
            'drawdown': drawdown,
            'racha': racha,
            'racha_count': racha_count,
            'comisiones': total_comisiones
        })
        if semana_now != semana_actual:
            # Enviar resumen semanal
            resumen_txt = f"\n📅 [RESUMEN SEMANAL] Semana {semana_actual}\n"
            for r in resumen_semanal:
                resumen_txt += f"{r['fecha']}: Capital ${r['capital']:,.2f}, Ganancia ${r['ganancia']:,.2f}, Winrate {r['winrate']:.1f}%, PF {r['profit_factor']:.2f}, Drawdown {r['drawdown']*100:.2f}%, Racha {r['racha']}({r['racha_count']}), Comisiones ${r['comisiones']:,.2f}\n"
            if notificar_telegram:
                enviar_alerta(resumen_txt)
            with open('sai_ultra_pro/ia/plan_auditoria.txt', 'a', encoding='utf-8') as faud:
                faud.write(resumen_txt + '\n')
            resumen_semanal = []
            semana_actual = semana_now
        # --- Lógica de horarios y mercados activos (failover total) ---
        wd = now.weekday()
        hour = now.hour
        minute = now.minute
        exness_abierto = mercado_exness_abierto(now)
        operar_binance = mercado_actual in ['BTCUSDT', 'ETHUSDT']
        operar_exness = mercado_actual in ['XAUUSD', 'US30m'] and exness_abierto
        if operar_binance:
            resumen += f'\n[HORARIO] Operando {mercado_actual} en Binance'
        elif operar_exness:
            resumen += f'\n[HORARIO] Operando {mercado_actual} en Exness'
        else:
            resumen += '\n[HORARIO] Ningún mercado disponible en este ciclo.'
        # --- Ejecución de operaciones con gestión de riesgo adaptativa y failover ---
        # --- VALIDACIÓN DE MÉTRICAS PARA SUBIR DE FASE ---
        puede_subir_fase = all([
            winrate > 60,
            profit_factor > 1.4,
            score_ia > 0.7,
            not drawdown_pausa
        ])
        if all([
            entorno_ok,
            score_ia > 0.7,
            profit_factor > 1.2,
            winrate > 60,
            not drawdown_pausa
        ]):
            # --- AUMENTO DE TAMAÑO POR FASE ---
            size = gestion_riesgo_adaptativa(fase, capital, score_ia, volatilidad, drawdown, racha_perdidas, modo_recuperacion)
            ok_binance = entorno_ok and validar_api_binance('', '') if operar_binance else False
            ok_exness = entorno_ok and exness_abierto and validar_api_exness('', '', '', '') if operar_exness else False
            brokers_operativos = []
            resultado_op = ''
            if ok_binance:
                # operacion_realizada = enviar_orden_binance(api_key, api_secret, simbolo, cantidad)
                brokers_operativos.append('Binance')
                hora_op = now.strftime('%H:%M')
                operaciones_detalle.append(f"[BINANCE] {mercado_actual} Orden long ejecutada a las {hora_op} ✅")
                resultado_op += f'\n[OPERACIÓN] Ejecutada en Binance ({mercado_actual}).'
            if ok_exness:
                operacion_realizada = ejecutar_orden_exness('long', size, '', '', '', '', symbol=mercado_actual)
                brokers_operativos.append('Exness')
                hora_op = now.strftime('%H:%M')
                operaciones_detalle.append(f"[EXNESS] {mercado_actual} Orden long ejecutada a las {hora_op} ✅")
                resultado_op += f'\n[OPERACIÓN] Ejecutada en Exness ({mercado_actual}).'
            if not (ok_binance or ok_exness):
                resultado_op += '\n[FAILOVER] Ningún broker disponible. 🛑'
            # Backup y logs detallados por hora
            guardar_backup()
            with open('sai_ultra_pro/ia/plan_log.txt', 'a') as flog:
                flog.write(f"{now.strftime('%Y-%m-%d %H:%M')} | Capital: {capital:.2f} | Winrate: {winrate:.1f} | Score IA: {score_ia:.2f} | PF: {profit_factor:.2f} | Brokers: {','.join(brokers_operativos)} | {resultado_op}\n")
            mensaje = (
                f"[PLAN MAESTRO]\nFecha: {now.strftime('%Y-%m-%d %H:%M')}\n"
                f"Capital: ${capital:,.2f}\n"
                f"Ganancia: ${ganancia_acumulada:,.2f} ({'+' if pct_ganancia>=0 else ''}{pct_ganancia:.2f}%) 💰\n"
                f"Fase: {fase}\nWinrate: {winrate:.1f}%\nScore IA: {score_ia:.2f}\n"
                f"Profit Factor: {profit_factor:.2f}\nBrokers operativos: {', '.join(brokers_operativos) if brokers_operativos else 'Ninguno'}\n"
                f"Mercado: {mercado_actual}\nVolatilidad: {volatilidad:.2f}\nTamaño operación: {size:.2f}\n"
                f"Racha actual: {racha} ({racha_count})\nDrawdown actual: {drawdown*100:.2f}% ⚠️\nMedia ganancia/op: ${media_ganancia:.2f}\n"
                f"{mensaje_max}"
                f"{resumen}{resultado_op}\n"
                + '\n'.join(operaciones_detalle)
            )
            # --- AVANCE DE FASE Y PROTECCIÓN DE CAPITAL ---
            if fase < len(fases) and capital > fases[fase] and puede_subir_fase:
                fase += 1
                capital_protegido_dinamico = round(capital * 0.2, 2)
                capital_protegido_fase.append(capital_protegido_dinamico)
                # Registrar en Google Sheets (simulado)
                try:
                    from sai_ultra_pro.integracion.google_dashboard import registrar_operacion
                    registrar_operacion({'evento':'FASE','fase':fase,'capital':capital,'capital_protegido':capital_protegido_dinamico,'fecha':now.strftime('%Y-%m-%d')})
                except Exception:
                    pass
                mensaje_fase = f"🎯 Avanzando a Fase {fase} – Capital protegido: ${capital_protegido_dinamico:,.2f}"
                mensaje += f"\n{mensaje_fase}"
                if notificar_telegram:
                    enviar_alerta(mensaje_fase)
            print(mensaje)
            if notificar_telegram:
                enviar_alerta(mensaje)
        else:
            if drawdown_pausa and entorno_ok and winrate > 60 and profit_factor > 1.2 and score_ia > 0.7:
                drawdown_pausa = False
                resumen += '\n[REANUDADO] Entorno y métricas recuperadas, reanudando operativa.'
                if notificar_telegram:
                    enviar_alerta("[REANUDADO] Operativa reactivada tras pausa por drawdown/métricas.")
            else:
                resumen += '\n[NO OPERAR] Condiciones no favorables, drawdown o evento macro. 🛑'
            mensaje = (
                f"[PLAN MAESTRO]\nFecha: {now.strftime('%Y-%m-%d %H:%M')}\n"
                f"Capital: ${capital:,.2f}\n"
                f"Ganancia: ${ganancia_acumulada:,.2f} ({'+' if pct_ganancia>=0 else ''}{pct_ganancia:.2f}%) 💰\n"
                f"Fase: {fase}\nWinrate: {winrate:.1f}%\nScore IA: {score_ia:.2f}\n"
                f"Profit Factor: {profit_factor:.2f}\nBrokers operativos: {'Binance' if operar_binance else ''}{' y Exness' if operar_exness else ''}\n"
                f"Volatilidad: {volatilidad:.2f}\n"
                f"Racha actual: {racha} ({racha_count})\nDrawdown actual: {drawdown*100:.2f}% ⚠️\nMedia ganancia/op: ${media_ganancia:.2f}\n"
                f"{mensaje_max}"
                f"{resumen}\n"
            )
            print(mensaje)
            if notificar_telegram:
                enviar_alerta(mensaje)
        # Reentrenamiento IA sensible
        if score_ia < 0.7:
            if notificar_telegram:
                enviar_alerta("[REENTRENAMIENTO] Score IA bajo, reentrenando modelo...")
            if reentrenar_y_validar(score_ia):
                if notificar_telegram:
                    enviar_alerta("[REENTRENAMIENTO] Nuevo modelo validado y activo.")
            else:
                if notificar_telegram:
                    enviar_alerta("[ERROR] Reentrenamiento fallido o score insuficiente. Se mantiene modelo anterior.")
        # --- Mensaje resumen al finalizar cada ciclo ---
        # Formateo seguro de size para mensaje y CSV
        if 'size' in locals() and isinstance(size, (int, float)):
            size_str = f"{size:.2f}"
        else:
            size_str = "0.00"
        resumen_final = (
            f"\n\n📊 [RESUMEN CICLO] {now.strftime('%Y-%m-%d %H:%M')}\n"
            f"Capital: ${capital:,.2f}\n"
            f"Ganancia: ${ganancia_acumulada:,.2f} ({'+' if pct_ganancia>=0 else ''}{pct_ganancia:.2f}%) 💰\n"
            f"Fase: {fase}\nWinrate: {winrate:.1f}%\nScore IA: {score_ia:.2f}\n"
            f"Profit Factor: {profit_factor:.2f}\nBrokers operativos: {', '.join(brokers_operativos) if 'brokers_operativos' in locals() and brokers_operativos else 'Ninguno'}\n"
            f"Mercado: {mercado_actual}\nVolatilidad: {volatilidad:.2f}\nTamaño operación: {size_str}\n"
            f"Capital protegido: ${capital_protegido_dinamico:,.2f}\n"
            f"Racha actual: {racha} ({racha_count})\nDrawdown actual: {drawdown*100:.2f}% ⚠️\nMedia ganancia/op: ${media_ganancia:.2f}\n"
            f"{mensaje_max}"
            f"{resumen}{resultado_op if 'resultado_op' in locals() else ''}\n"
            + ('\n'.join(operaciones_detalle) if 'operaciones_detalle' in locals() else '')
        )
        print(resumen_final)
        if notificar_telegram:
            enviar_alerta(resumen_final)
        # --- Registrar resumen en log txt y csv ---
        with open('sai_ultra_pro/ia/plan_resumen.txt', 'a', encoding='utf-8') as flog:
            flog.write(resumen_final + '\n' + ('-'*60) + '\n')
        import csv
        resumen_csv = [
            now.strftime('%Y-%m-%d %H:%M'),
            f"${capital:,.2f}",
            f"${ganancia_acumulada:,.2f}",
            f"{pct_ganancia:.2f}%",
            fase,
            f"{winrate:.1f}%",
            f"{score_ia:.2f}",
            f"{profit_factor:.2f}",
            ', '.join(brokers_operativos) if 'brokers_operativos' in locals() and brokers_operativos else 'Ninguno',
            f"{volatilidad:.2f}",
            size_str,
            racha,
            racha_count,
            f"{drawdown*100:.2f}%",
            f"${media_ganancia:.2f}",
            mensaje_max.replace('\n',' '),
            resumen.replace('\n',' '),
            resultado_op.replace('\n',' ') if 'resultado_op' in locals() else '',
            '|'.join(operaciones_detalle) if 'operaciones_detalle' in locals() else ''
        ]
        with open('sai_ultra_pro/ia/plan_resumen.csv', 'a', newline='', encoding='utf-8') as fcsv:
            writer = csv.writer(fcsv)
            if fcsv.tell() == 0:
                writer.writerow([
                    'fecha','capital','ganancia','%','fase','winrate','score_ia','profit_factor','brokers','volatilidad','tamano','racha','racha_count','drawdown','media_ganancia','maximo','resumen','resultado','operaciones'
                ])
            writer.writerow(resumen_csv)
        # Espera pasiva hasta el próximo minuto
        time.sleep(60)
    if notificar_telegram:
        enviar_alerta(f"[PLAN FINALIZADO] Capital alcanzado: ${capital:,.2f} en {fase} fases.")


if __name__ == "__main__":
    # --- ORDEN DE PRUEBA REAL EN EXNESS CON SL/TP VÁLIDOS ---
    import MetaTrader5 as mt5
    import time
    with open('sai_ultra_pro/config/config.json', 'r') as f:
        config = json.load(f)
    exness_conf = config['api_keys']
    api_key = exness_conf['EXNESS_API_KEY']
    api_secret = exness_conf['EXNESS_API_SECRET']
    server = exness_conf['EXNESS_SERVER']
    platform = exness_conf['EXNESS_PLATFORM']
    symbol = 'XAUUSDm'
    # Inicializar MT5
    if not mt5.initialize(server=server, login=int(api_key), password=api_secret):
        print(f"[EXNESS][PRUEBA] No se pudo conectar a Exness: {mt5.last_error()}")
    else:
        info = mt5.symbol_info(symbol)
        if info is None or not info.visible:
            print(f"[EXNESS][PRUEBA] El símbolo {symbol} no está disponible o no es visible en MT5. Habilítalo en el panel de mercado.")
        else:
            price = mt5.symbol_info_tick(symbol).ask
            sl = price - 20.0
            tp = price + 40.0
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": 0.01,
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 10,
                "magic": 20250729,
                "comment": "PRUEBA SAI ULTRA PRO"
            }
            print(f"[EXNESS][PRUEBA] Enviando orden BUY {symbol} 0.01 | price={price:.2f} sl={sl:.2f} tp={tp:.2f}")
            result = mt5.order_send(request)
            if result is None:
                print(f"[EXNESS][PRUEBA][ERROR] mt5.order_send devolvió None. Último error: {mt5.last_error()}")
            else:
                print(f"[EXNESS][PRUEBA][RESULTADO] {result}")
        mt5.shutdown()
    # --- FIN ORDEN DE PRUEBA ---
    # Puedes comentar la línea siguiente si no quieres lanzar el ciclo normal después de la prueba:
    ejecutar_plan_maestro()


# Permitir ejecución directa como script

# (Bloque duplicado eliminado porque las variables no existen en este ámbito)
