
import json
from sai_ultra_pro.net.http import post


def enviar_alerta(mensaje):
    try:
        with open('sai_ultra_pro/config/config.json') as f:
            config = json.load(f)
        token = config['api_keys'].get('TELEGRAM_BOT_TOKEN', '')
        chat_id = config['api_keys'].get('TELEGRAM_CHAT_ID', '')
        if not token or not chat_id:
            print("[TELEGRAM] Faltan credenciales de Telegram en config.json")
            return
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        # Truncar mensaje si es muy largo para Telegram (máx 4096 caracteres)
        mensaje_str = str(mensaje)
        if len(mensaje_str) > 4000:
            mensaje_str = mensaje_str[:3990] + "... [truncado]"
        data = {"chat_id": chat_id, "text": mensaje_str}
        try:
            r = post(url, data=data)
            if r.status_code == 200:
                print(f"[TELEGRAM] Mensaje enviado: {mensaje_str}")
            else:
                print(f"[TELEGRAM] Error al enviar mensaje: {r.text}")
        except Exception as e:
            print(f"[TELEGRAM] Error al enviar (http wrapper): {e}")
    except Exception as e:
        print(f"[TELEGRAM] Excepción: {e}")
