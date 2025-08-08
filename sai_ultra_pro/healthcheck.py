
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from integracion.telegram_alertas import enviar_alerta
from main import validar_api_binance, validar_api_exness
from ia.analizador_volatilidad import AnalizadorVolatilidad
from ia.analizador_volatilidad_exness import AnalizadorVolatilidadExness
import logging
from tensorflow.keras.models import load_model

logging.basicConfig(filename='sai_ultra_pro/ia/healthcheck.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

CONFIG_PATH = 'sai_ultra_pro/config/config.json'
OPS_PATH = 'sai_ultra_pro/ia/ops_real.csv'
OPS_EXNESS_PATH = 'sai_ultra_pro/ia/ops_exness.csv'
RETRAIN_PATH = 'sai_ultra_pro/ia/last_retrain.txt'
BACKUP_PATH = 'sai_ultra_pro/ia/modelo_transformer_backup.h5'
WATCHDOG_PATH = 'sai_ultra_pro/monitor/watchdog.py'


def healthcheck():
    resumen = '[HEALTHCHECK SAI ULTRA PRO]\n'
    # 1. Estado de conexión a Binance y Exness
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        api_binance = config['api_keys']['BINANCE_API_KEY']
        api_binance_secret = config['api_keys']['BINANCE_API_SECRET']
        api_exness = config['api_keys']['EXNESS_API_KEY']
        api_exness_secret = config['api_keys']['EXNESS_API_SECRET']
        server = config['api_keys']['EXNESS_SERVER']
        platform = config['api_keys']['EXNESS_PLATFORM']
        ok_binance = validar_api_binance(api_binance, api_binance_secret)
        ok_exness = validar_api_exness(api_exness, api_exness_secret, server, platform)
        resumen += f'Binance: {"OK" if ok_binance else "FALLO"} | Exness: {"OK" if ok_exness else "FALLO"}\n'
    except Exception as e:
        resumen += f'[ERROR] Estado conexión: {e}\n'
        logging.error(f'Conexión: {e}')
    # 2. Última operación ejecutada
    try:
        op = None
        if os.path.exists(OPS_PATH):
            df = pd.read_csv(OPS_PATH)
            if len(df) > 0:
                op = df.iloc[-1]
        if op is not None:
            resumen += f'Última operación: {op.get("fecha", "?")} | {op.get("resultado", "?")} | Capital: {op.get("capital", "?")}\n'
        else:
            resumen += 'Última operación: N/D\n'
    except Exception as e:
        resumen += f'[ERROR] Última operación: {e}\n'
        logging.error(f'Última operación: {e}')
    # 3. Validación de datos
    try:
        valid = True
        if os.path.exists(OPS_PATH):
            df = pd.read_csv(OPS_PATH)
            if df.isnull().any().any():
                resumen += 'NaN detectados en operaciones. '
                valid = False
            if (df.select_dtypes(include=[float, int]) > 1e8).any().any():
                resumen += 'Outliers extremos detectados. '
                valid = False
        resumen += f'Integridad datos: {"OK" if valid else "FALLO"}\n'
    except Exception as e:
        resumen += f'[ERROR] Validación datos: {e}\n'
        logging.error(f'Validación datos: {e}')
    # 4. Último entorno de riesgo
    try:
        activos = config.get('activos', ['BTCUSDT'])
        entorno = {}
        for symbol in activos:
            av = AnalizadorVolatilidad()
            av.symbol = symbol
            entorno[symbol] = av.evaluar_entorno()
        resumen += 'Entorno Binance: ' + ', '.join([f'{k}:{v}' for k,v in entorno.items()]) + '\n'
        symbols_exness = ['USDRUB', 'USDAED', 'USDBRL', 'US30m', 'US500m', 'USTECm']
        entorno_ex = {}
        for symbol in symbols_exness:
            avx = AnalizadorVolatilidadExness(symbol=symbol)
            entorno_ex[symbol] = avx.evaluar_entorno()
        resumen += 'Entorno Exness: ' + ', '.join([f'{k}:{v}' for k,v in entorno_ex.items()]) + '\n'
    except Exception as e:
        resumen += f'[ERROR] Entorno riesgo: {e}\n'
        logging.error(f'Entorno riesgo: {e}')
    # 5. Último reentrenamiento y score
    try:
        last_retrain = 'N/D'
        if os.path.exists(RETRAIN_PATH):
            with open(RETRAIN_PATH) as f:
                last_retrain = f.read().strip()
        resumen += f'Último reentrenamiento: {last_retrain}\n'
        # Score actual (último backtest)
        score = 'N/D'
        if os.path.exists('sai_ultra_pro/ia/backtest_score.log'):
            with open('sai_ultra_pro/ia/backtest_score.log') as f:
                score = f.readlines()[-1].strip()
        resumen += f'Score actual: {score}\n'
    except Exception as e:
        resumen += f'[ERROR] Reentrenamiento/score: {e}\n'
        logging.error(f'Reentrenamiento/score: {e}')
    # 6. Estado de backups y watchdog (con validación avanzada)
    try:
        backup_ok = os.path.exists(BACKUP_PATH)
        backup_alerta = ''
        backup_valido = False
        if backup_ok:
            stat = os.stat(BACKUP_PATH)
            fecha_mod = datetime.fromtimestamp(stat.st_mtime)
            ahora = datetime.now()
            dias = (ahora - fecha_mod).days
            tam_kb = stat.st_size / 1024
            if dias > 3:
                backup_alerta += f'[ALERTA] El backup del modelo es antiguo ({dias} días).\n'
            if tam_kb < 100:
                backup_alerta += '[ALERTA] El backup del modelo es muy pequeño (<100 KB).\n'
            # Intentar cargar el modelo
            try:
                load_model(BACKUP_PATH)
                backup_valido = True
            except Exception as e:
                backup_alerta += f'[ALERTA] El backup del modelo está corrupto: {e}\n'
                logging.error(f'Backup corrupto: {e}')
        else:
            backup_alerta += '[ALERTA] No existe el archivo de backup del modelo.\n'
        watchdog_ok = os.path.exists(WATCHDOG_PATH)
        resumen += f'Backup modelo: {"OK" if backup_ok and backup_valido and not backup_alerta else "FALLO"} | Watchdog: {"OK" if watchdog_ok else "FALLO"}\n'
        if backup_alerta:
            resumen += backup_alerta
            try:
                enviar_alerta(backup_alerta)
            except Exception as e:
                logging.error(f'Alerta Telegram backup: {e}')
    except Exception as e:
        resumen += f'[ERROR] Backup/Watchdog: {e}\n'
        logging.error(f'Backup/Watchdog: {e}')
    # Consola y Telegram
    print(resumen)
    try:
        enviar_alerta(resumen)
    except Exception as e:
        logging.error(f'Envío Telegram: {e}')

if __name__ == "__main__":
    healthcheck()
