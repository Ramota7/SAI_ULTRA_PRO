import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Script de test para disparar todas las alertas Telegram en orden
from sai_ultra_pro.integracion.telegram_alertas import enviar_alerta
import time
import os


def test_alertas_telegram():
    mensajes = [
        "✅ Bot iniciado correctamente",
        "🟢 Nuevo ciclo de trading #1",
        "💼 Operación ejecutada\nBroker: binance\nEstrategia: Momentum\nSímbolo: BTCUSDT\nTipo: long\nCapital: $100.00",
        "💼 Operación ejecutada\nBroker: exness\nEstrategia: Arbitraje\nSímbolo: ETHUSD\nTipo: short\nCapital: $200.00",
        "🔁 Rotación de estrategia: ahora activa Arbitraje",
        "📊 Resumen de ciclo #1:\nOperaciones: 2\nbinance | Momentum | BTCUSDT | long | $100.00\nexness | Arbitraje | ETHUSD | short | $200.00",
        "⛔ Ciclo bloqueado por protección activa.",
        "🔒 Capital protegido activado: solo capital protegido disponible, operaciones pausadas.",
        "📉 Drawdown alto detectado: reducción de riesgo o pausa operativa.",
        "🕐 Restricción por horario activada: fuera del rango permitido.",
        "⛔ Protección de racha de pérdidas activada\nRacha detectada: 3\nUmbral actual: 3",
        "🧠 Autoajuste de umbral de racha de pérdidas\nNuevo valor: 3\nProfit factor: 1.25",
        "📁 Backup automático guardado exitosamente",
        "📝 config.json actualizado",
        "📊 Histórico de umbrales actualizado",
        "🧪 Modo simulación activado",
        "🔐 API Key comprometida o inválida",
        "💳 Saldo insuficiente para operar",
        "🌐 Problemas de conexión al broker o latencia alta"
    ]
    # En entorno de CI/local lento la prueba puede tomar >3s; para pruebas rápidas
    # activar ENV TEST_FAST=1 para reducir sleeps a 0.01s.
    fast = os.environ.get('TEST_FAST', '') == '1'
    sleep_sec = 0.01 if fast else 1
    for msg in mensajes:
        print(f"Enviando alerta: {msg}")
        enviar_alerta(msg)
        time.sleep(sleep_sec)  # Pausa para evitar flood

if __name__ == "__main__":
    test_alertas_telegram()
