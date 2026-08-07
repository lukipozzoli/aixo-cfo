import os

# Configuración del canal por donde el agente habla con el usuario.

MESSAGING_PROVIDER: str = os.environ["MESSAGING_PROVIDER"]

# Los datos que necesita el proveedor elegido, listos para pasarle al factory.
#
# El if es el punto de todo esto: las variables de Telegram se leen SOLO si
# Telegram es el proveedor elegido. Antes se leían siempre, así que alguien que
# usara otro canal igual estaba obligado a tener un token de Telegram para que
# el sistema arrancara.
#
# Las claves del diccionario coinciden con los parámetros del constructor de
# cada provider, porque main.py lo pasa con ** (desarma el diccionario en
# argumentos con nombre).
if MESSAGING_PROVIDER == "telegram":
    MESSAGING_CONFIG: dict = {
        "token": os.environ["TELEGRAM_BOT_TOKEN"],
        # webhook o polling. Vive acá y no como variable suelta porque es un
        # detalle de cómo se conecta este proveedor, no del sistema.
        "mode": os.environ["MESSAGING_MODE"],
        "port": int(os.environ["MESSAGING_PORT"]),
        # Opcional: solo hace falta en modo webhook. En polling no hay ninguna
        # URL pública a la que Telegram deba apuntar. os.getenv devuelve None
        # si no está, en vez de reventar.
        "webhook_url": os.getenv("TELEGRAM_WEBHOOK_URL"),
        "webhook_path": os.environ["TELEGRAM_WEBHOOK_PATH"],
    }
else:
    # Un provider desconocido no llega a usar esto: el factory lo rechaza antes.
    MESSAGING_CONFIG = {}

# Destino de los mensajes que el agente manda sin que nadie haya preguntado
# (reportes diarios, alertas). Todavía no lo usa nadie porque no existen los
# cron jobs, pero se conserva para cuando existan. Ver APR-152.
#
# Es opcional a propósito: hoy el sistema funciona perfecto sin esto, así que
# exigirlo sería frenar el arranque por una función que aún no existe.
TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")
