import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model
import os

def cargar_datos(nombre):
    import ta
    ruta = os.path.join(os.path.dirname(__file__), nombre)
    df = pd.read_csv(ruta)
    # Si faltan columnas técnicas, agrégalas
    if 'rsi' not in df.columns:
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    if 'sma20' not in df.columns:
        df['sma20'] = ta.trend.sma_indicator(df['close'], window=20)
    if 'volatilidad' not in df.columns:
        df['volatilidad'] = df['close'].rolling(10).std()
    df = df.dropna().reset_index(drop=True)
    return df

def simular_trading(df, modelo, window=20, threshold=0.6, tp=0.003, sl=0.0015):
    features = ['open','high','low','close','volume','rsi','sma20','volatilidad']
    capital = 1000
    balance = [capital]
    operaciones = []
    for i in range(window, len(df)-1):
        x = df[features].iloc[i-window:i].values
        x = (x - x.mean(axis=0)) / (x.std(axis=0)+1e-8)
        x = x.reshape((1, window, len(features)))
        prob = float(modelo.predict(x)[0][0])
        if prob > threshold:
            # Simula LONG
            entry = df['close'].iloc[i]
            max_after = df['high'].iloc[i+1:i+10].max()
            min_after = df['low'].iloc[i+1:i+10].min()
            take_profit = entry * (1+tp)
            stop_loss = entry * (1-sl)
            if max_after >= take_profit:
                resultado = 'TP'
                capital += capital*tp
            elif min_after <= stop_loss:
                resultado = 'SL'
                capital -= capital*sl
            else:
                resultado = 'NEUTRO'
            operaciones.append({'i':i,'entry':entry,'prob':prob,'resultado':resultado,'capital':capital})
            balance.append(capital)
    return pd.DataFrame(operaciones), balance

if __name__ == "__main__":
    df = cargar_datos('data_BTCUSDT_15m.csv')
    modelo = load_model(os.path.join(os.path.dirname(__file__), 'modelo_transformer.h5'))
    ops, balance = simular_trading(df, modelo)
    print(ops.tail())
    print(f'Capital final: {balance[-1]:.2f}')
    print(f'Operaciones: {len(ops)} | Winrate: {100*sum(ops["resultado"]=="TP")/len(ops):.1f}%')
