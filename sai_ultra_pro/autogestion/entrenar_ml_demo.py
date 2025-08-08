"""
Script de ejemplo para entrenar el modelo ML de señales con datos simulados.
Puedes reemplazar los datos por tus señales reales.
"""
import pandas as pd
from ml_signals import entrenar_modelo

def generar_datos_demo(n=200):
    import numpy as np
    # Simula features y etiquetas (1=éxito, 0=fallo)
    X = pd.DataFrame({
        'feature1': np.random.uniform(0.005, 0.03, n),
        'feature2': np.random.randint(2, 6, n)
    })
    # Etiqueta: éxito si feature1 alto y feature2 alto
    X['label'] = ((X['feature1'] > 0.015) & (X['feature2'] >= 4)).astype(int)
    return X

def main():
    datos = generar_datos_demo()
    modelo = entrenar_modelo(datos)
    print("Modelo entrenado y guardado.")

if __name__ == "__main__":
    main()
