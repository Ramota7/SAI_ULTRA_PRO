

import numpy as np
import pandas as pd
import requests
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils import resample
import os
import sys
import ta  # pip install ta
from keras.callbacks import EarlyStopping
try:
    import ta  # pip install ta
except ImportError:
    raise ImportError("Falta el paquete 'ta'. Instálalo con: pip install ta")

# Función para encontrar el valor máximo de limit permitido por la API de Binance
def encontrar_limit_maximo(symbol='BTCUSDT', interval='15m', limit_inicial=1500, limit_min=100, paso=100):
    limit = limit_inicial
    while limit >= limit_min:
        url = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}'
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                print(f"[INFO] limit permitido: {limit}")
                return limit
            else:
                print(f"[WARN] limit={limit} no permitido: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"[ERROR] limit={limit} falló: {e}")
        limit -= paso
    print(f"[ERROR] No se encontró un valor válido de limit entre {limit_inicial} y {limit_min}")
    return limit_min

# 1. Descarga de datos históricos de Binance (ejemplo BTCUSDT 15m)

def descargar_datos_binance(symbol='BTCUSDT', interval='15m', limit=500):
    url = f'https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}'
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"[ERROR] Descarga fallida: {r.status_code} - {r.text}")
            return pd.DataFrame()
        data = r.json()
    except Exception as e:
        print(f"[ERROR] Descarga fallida: {e}")
        return pd.DataFrame()
    if not data or not isinstance(data, list):
        print(f"[ERROR] Respuesta vacía o inesperada de Binance: {data}")
        return pd.DataFrame()
    df = pd.DataFrame(data, columns=[
        'open_time','open','high','low','close','volume','close_time','qav','trades','taker_base_vol','taker_quote_vol','ignore'])
    df = df[['open','high','low','close','volume']].astype(float)
    # Indicadores técnicos
    try:
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        df['sma20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['volatilidad'] = df['close'].rolling(10).std()
    except Exception as e:
        print(f"[ERROR] Error calculando indicadores: {e}")
        return pd.DataFrame()
    df = df.dropna().reset_index(drop=True)
    return df

# 2. Preprocesamiento y generación de etiquetas (simulación: éxito si close > open en la siguiente vela)

def preparar_datos(df, window=20):
    X, y = [], []
    features = ['open','high','low','close','volume','rsi','sma20','volatilidad']
    for i in range(len(df)-window-1):
        X.append(df[features].iloc[i:i+window].values)
        y.append(1 if df.iloc[i+window]['close'] > df.iloc[i+window]['open'] else 0)
    X, y = np.array(X), np.array(y)
    return X, y

# 3. Definición del modelo LSTM

def crear_modelo(input_shape):
    model = Sequential([
        Bidirectional(LSTM(64, return_sequences=True), input_shape=input_shape),
        Dropout(0.3),
        LSTM(32),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model



def entrenar_modelo(symbol='BTCUSDT', interval='15m', limit=None):
    """
    Entrena el modelo IA con los datos más recientes y guarda el modelo actualizado.
    Si limit es None, busca automáticamente el máximo permitido por la API.
    """
    if limit is None:
        print("[INFO] Buscando el valor máximo de limit permitido por Binance...")
        limit = encontrar_limit_maximo(symbol=symbol, interval=interval)
        print(f"[INFO] Usando limit={limit}")
    df = descargar_datos_binance(symbol=symbol, interval=interval, limit=limit)
    print('Datos descargados:', df.shape)
    if df.shape[0] == 0:
        print('[ERROR] No se descargaron datos. Abortando entrenamiento.')
        return False
    X, y = preparar_datos(df)
    print('Secuencias generadas:', X.shape)
    if X.shape[0] == 0:
        print('[ERROR] No se generaron secuencias. Abortando entrenamiento.')
        return False
    X_reshaped = X.reshape(-1, X.shape[-1])
    scaler = StandardScaler().fit(X_reshaped)
    X_scaled = scaler.transform(X_reshaped).reshape(X.shape)
    X0, y0 = X_scaled[y==0], y[y==0]
    X1, y1 = X_scaled[y==1], y[y==1]
    if len(y0) > len(y1) and len(y1) > 0:
        X0, y0 = resample(X0, y0, replace=False, n_samples=len(y1), random_state=42)
    elif len(y1) > len(y0) and len(y0) > 0:
        X1, y1 = resample(X1, y1, replace=False, n_samples=len(y0), random_state=42)
    if len(y0) == 0 or len(y1) == 0:
        print('[ERROR] No hay suficientes datos de ambas clases para balancear.')
        return False
    Xb = np.concatenate([X0, X1])
    yb = np.concatenate([y0, y1])
    print('Clases balanceadas:', np.bincount(yb))
    if Xb.shape[0] == 0:
        print('[ERROR] No hay datos balanceados. Abortando entrenamiento.')
        return False
    X_train, X_test, y_train, y_test = train_test_split(Xb, yb, test_size=0.2, random_state=42)
    model = crear_modelo((Xb.shape[1], Xb.shape[2]))
    es = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
    model.fit(X_train, y_train, epochs=30, batch_size=32, validation_split=0.1, callbacks=[es])
    loss, acc = model.evaluate(X_test, y_test)
    print(f"Test accuracy: {acc:.2f}")
    ruta = os.path.join(os.path.dirname(__file__), 'modelo_transformer.h5')
    model.save(ruta)
    print(f"Modelo guardado en {ruta}")
    return True



if __name__ == "__main__":
    # Permitir pasar limit como argumento: python entrenar_modelo.py [limit]
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except Exception:
            print(f"[WARN] Argumento inválido para limit: {sys.argv[1]}. Usando búsqueda automática.")
            limit = None
    entrenar_modelo(limit=limit)
