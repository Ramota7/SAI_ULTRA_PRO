import pandas as pd
import ta
import os

def enriquecer_csv(path_csv):
    df = pd.read_csv(path_csv)
    # Asegurar nombres estándar
    df.columns = [c.lower() for c in df.columns]
    # Calcular indicadores
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['volatilidad'] = df['close'].rolling(window=20).std()
    # Eliminar filas con NaN
    df = df.dropna().reset_index(drop=True)
    df.to_csv(path_csv, index=False)
    print(f"Archivo enriquecido y guardado: {path_csv}")

if __name__ == "__main__":
    ruta = os.path.join(os.path.dirname(__file__), 'data_BTCUSDT_15m.csv')
    enriquecer_csv(ruta)
