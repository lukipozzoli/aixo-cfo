from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Awaitable


@dataclass
class Attachment:
    # Archivo adjunto normalizado, independiente del proveedor.
    # Cada provider mapea su formato nativo a esta estructura.
    type: str             # "image", "document", "audio", "video", "voice"
    file_id: str | None   # ID interno del provider (ej: Telegram file_id), para descarga posterior
    url: str | None       # URL pública si está disponible directamente
    mime_type: str | None
    file_name: str | None


@dataclass
class IncomingMessage:
    # Formato normalizado de mensaje entrante, independiente del proveedor.
    # Todos los providers deben mapear su payload crudo a esta estructura.
    provider: str                        # "telegram", "imessage", etc.
    chat_id: str                         # identificador del chat, usado para responder
    user_id: str                         # identificador del usuario que envió el mensaje
    text: str | None                     # None si el mensaje es solo un archivo adjunto
    attachments: list[Attachment] = field(default_factory=list)  # vacío si es solo texto
    raw: dict = field(default_factory=dict)  # payload original sin modificar


class MessagingProvider(ABC):
    # Interfaz genérica para cualquier proveedor de mensajería.
    # Los agentes solo interactúan con esta abstracción, nunca con Telegram directamente.
    #
    # Para agregar un nuevo proveedor (ej: iMessage, WhatsApp, Slack):
    #   1. Crear providers/messaging/<nombre>.py
    #   2. Implementar esta clase: send() y listen()
    #   3. En listen(), mapear mensajes entrantes (texto y archivos) a IncomingMessage y Attachment
    #   4. Registrarlo en messaging/client.py con su nombre como clave en el if/elif
    #   5. Agregar MESSAGING_PROVIDER=<nombre> al .env de la empresa

    @abstractmethod
    async def send(self, chat_id: str, text: str) -> None:
        # Envía un mensaje de texto al chat indicado.
        pass

    @abstractmethod
    async def listen(self, handler: Callable[[IncomingMessage], Awaitable[None]]) -> None:
        # Inicia el loop de escucha. Bloquea la ejecución.
        # handler es una corrutina que recibe cada mensaje entrante normalizado.
        pass
