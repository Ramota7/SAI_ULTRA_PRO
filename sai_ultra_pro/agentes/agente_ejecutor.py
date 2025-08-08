import logging
import time

class AgenteEjecutor:
    """
    Agente encargado de ejecutar operaciones de trading de forma robusta y profesional.
    """

    def __init__(self, broker_api, notificador=None):
        """
        broker_api: instancia de la API del broker (debe implementar buy/sell/cancel, etc.)
        notificador: función o clase para enviar notificaciones (opcional)
        """
        self.broker_api = broker_api
        self.notificador = notificador
        self.logger = logging.getLogger("AgenteEjecutor")
        self.logger.setLevel(logging.INFO)

    def ejecutar_operacion(self, operacion):
        """
        Ejecuta una operación de trading.
        operacion: dict con claves tipo {'tipo': 'compra'/'venta', 'activo': str, 'volumen': float, ...}
        Retorna True si la operación fue exitosa, False si falló.
        """
        try:
            self.logger.info(f"Intentando ejecutar operación: {operacion}")
            tipo = operacion.get('tipo')
            activo = operacion.get('activo')
            volumen = operacion.get('volumen')
            precio = operacion.get('precio', None)
            sl = operacion.get('sl', None)
            tp = operacion.get('tp', None)

            if not tipo or not activo or not volumen or volumen <= 0:
                raise ValueError("Datos de operación incompletos o inválidos.")

            if tipo == 'compra':
                resultado = self.broker_api.buy(activo, volumen, precio, sl, tp)
            elif tipo == 'venta':
                resultado = self.broker_api.sell(activo, volumen, precio, sl, tp)
            else:
                raise ValueError(f"Tipo de operación desconocido: {tipo}")

            if resultado.get('exito'):
                self.logger.info(f"Operación ejecutada exitosamente: {resultado}")
                if self.notificador:
                    self.notificador.enviar(f"✅ Operación ejecutada: {operacion}")
                return True
            else:
                self.logger.warning(f"Fallo al ejecutar operación: {resultado}")
                if self.notificador:
                    self.notificador.enviar(f"⚠️ Fallo al ejecutar operación: {operacion}\nMotivo: {resultado.get('mensaje')}")
                return False

        except Exception as e:
            self.logger.error(f"Error crítico al ejecutar operación: {e}", exc_info=True)
            if self.notificador:
                self.notificador.enviar(f"❌ Error crítico al ejecutar operación: {operacion}\nError: {e}")
            return False

    def cancelar_operacion(self, id_operacion):
        """
        Cancela una operación abierta.
        """
        try:
            self.logger.info(f"Intentando cancelar operación: {id_operacion}")
            resultado = self.broker_api.cancel(id_operacion)
            if resultado.get('exito'):
                self.logger.info(f"Operación cancelada exitosamente: {id_operacion}")
                if self.notificador:
                    self.notificador.enviar(f"🚫 Operación cancelada: {id_operacion}")
                return True
            else:
                self.logger.warning(f"Fallo al cancelar operación: {resultado}")
                if self.notificador:
                    self.notificador.enviar(f"⚠️ Fallo al cancelar operación: {id_operacion}\nMotivo: {resultado.get('mensaje')}")
                return False
        except Exception as e:
            self.logger.error(f"Error crítico al cancelar operación: {e}", exc_info=True)
            if self.notificador:
                self.notificador.enviar(f"❌ Error crítico al cancelar operación: {id_operacion}\nError: {e}")
            return False

    def ejecutar_batch(self, lista_operaciones, delay=0.5):
        """
        Ejecuta un batch de operaciones con retardo opcional entre ellas.
        """
        resultados = []
        for op in lista_operaciones:
            exito = self.ejecutar_operacion(op)
            resultados.append(exito)
            time.sleep(delay)
        return resultados