"""
Módulo de machine learning para filtrado y aprendizaje de señales.
Incluye entrenamiento, predicción y reentrenamiento automático.
"""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

MODEL_PATH = 'sai_ultra_pro/autogestion/modelo_signals.pkl'

def entrenar_modelo(datos):
    """
    Entrena un modelo de clasificación de señales.
    datos: DataFrame con columnas ['feature1', 'feature2', ..., 'label']
    """
    X = datos.drop('label', axis=1)
    y = datos['label']
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X, y)
    joblib.dump(clf, MODEL_PATH)
    return clf

def predecir_probabilidad(signal_features):
    """
    Predice la probabilidad de éxito de una señal.
    signal_features: DataFrame o dict con las features de la señal
    """
    if not os.path.exists(MODEL_PATH):
        return 0.5  # Sin modelo, probabilidad neutra
    clf = joblib.load(MODEL_PATH)
    if isinstance(signal_features, dict):
        import numpy as np
        X = pd.DataFrame([signal_features])
    else:
        X = signal_features
    proba = clf.predict_proba(X)[0][1]
    return proba

def reentrenar_periodicamente(datos):
    """
    Reentrena el modelo con los datos más recientes.
    """
    return entrenar_modelo(datos)
