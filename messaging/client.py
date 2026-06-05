from core.messaging.base import MessagingProvider
from config.aixo import (
    MESSAGING_PROVIDER,
    MESSAGING_MODE,
    MESSAGING_PORT,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_WEBHOOK_URL,
    TELEGRAM_WEBHOOK_PATH,
)

# Factory del proveedor de mensajería para AIXO.
# Si en el futuro se cambia de Telegram, solo se cambia MESSAGING_PROVIDER en .env.
_client: MessagingProvider | None = None


def get_client() -> MessagingProvider:
    global _client
    if _client is None:
        if MESSAGING_PROVIDER == "telegram":
            from providers.messaging.telegram import TelegramProvider
            _client = TelegramProvider(
                token=TELEGRAM_BOT_TOKEN,
                mode=MESSAGING_MODE,
                port=MESSAGING_PORT,
                webhook_url=TELEGRAM_WEBHOOK_URL,
                webhook_path=TELEGRAM_WEBHOOK_PATH,
            )
        else:
            raise ValueError(f"Provider de mensajería desconocido: '{MESSAGING_PROVIDER}'.")
    return _client
