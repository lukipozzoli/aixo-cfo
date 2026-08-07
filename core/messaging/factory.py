from core.messaging.base import MessagingProvider


def build_messaging_provider(provider: str, **config) -> MessagingProvider:
    # Devuelve el proveedor de mensajería que corresponda según el nombre.
    #
    # Recibe la config por parámetro en vez de leerla de config/: por eso este
    # archivo puede vivir en core/ y servir para cualquier empresa. Quien decide
    # qué pasarle es main.py, que es el único lugar que sabe de configuración.
    #
    # **config junta el resto de los argumentos en un diccionario. Es necesario
    # porque cada proveedor pide datos distintos: Telegram quiere token y
    # webhook, otro querría otra cosa. Así el factory no tiene que conocer de
    # antemano los parámetros de todos.
    if provider == "telegram":
        # El import va adentro del if para no cargar la librería de un proveedor
        # que no se va a usar.
        from providers.messaging.telegram import TelegramProvider
        return TelegramProvider(**config)
    else:
        raise ValueError(f"Provider de mensajería desconocido: '{provider}'. Opciones válidas: telegram.")
