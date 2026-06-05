import httpx
import uvicorn
from fastapi import FastAPI, Request
from typing import Callable, Awaitable
from core.messaging.base import MessagingProvider, IncomingMessage, Attachment


class TelegramProvider(MessagingProvider):
    # Implementación de MessagingProvider para Telegram.
    # Soporta dos modos configurables via MESSAGING_MODE:
    #   - webhook: Telegram hace POST a la URL pública. Requiere Ngrok en local.
    #   - polling: el bot consulta a Telegram en loop. No requiere URL pública.

    def __init__(self, token: str, mode: str, port: int, webhook_url: str | None, webhook_path: str):
        self._token = token
        self._mode = mode
        self._port = port
        self._webhook_url = webhook_url
        self._webhook_path = webhook_path
        self._base_url = f"https://api.telegram.org/bot{token}"

    async def send(self, chat_id: str, text: str) -> None:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self._base_url}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )

    async def listen(self, handler: Callable[[IncomingMessage], Awaitable[None]]) -> None:
        if self._mode == "webhook":
            await self._listen_webhook(handler)
        elif self._mode == "polling":
            await self._listen_polling(handler)
        else:
            raise ValueError(f"Modo desconocido: '{self._mode}'. Opciones válidas: webhook, polling.")

    async def _listen_webhook(self, handler: Callable[[IncomingMessage], Awaitable[None]]) -> None:
        # Registra la URL pública con Telegram y levanta el servidor FastAPI.
        # En local: TELEGRAM_WEBHOOK_URL es la URL de Ngrok. En prod: la URL del servidor.
        if not self._webhook_url:
            raise ValueError("TELEGRAM_WEBHOOK_URL es requerido en modo webhook.")

        await self._register_webhook()

        app = FastAPI()

        @app.post(self._webhook_path)
        async def webhook(request: Request):
            data = await request.json()
            message = data.get("message") or data.get("edited_message")
            if message:
                incoming = self._normalize(message, data)
                if incoming:
                    await handler(incoming)
            return {"ok": True}

        config = uvicorn.Config(app, host="0.0.0.0", port=self._port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    async def _listen_polling(self, handler: Callable[[IncomingMessage], Awaitable[None]]) -> None:
        # Polling largo: Telegram mantiene la conexión abierta hasta 30s antes de responder vacío.
        # offset asegura que cada update se procese una sola vez.
        offset = None
        async with httpx.AsyncClient() as client:
            while True:
                params: dict = {"timeout": 30}
                if offset is not None:
                    params["offset"] = offset
                response = await client.get(
                    f"{self._base_url}/getUpdates",
                    params=params,
                    timeout=35,
                )
                updates = response.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    message = update.get("message") or update.get("edited_message")
                    if message:
                        incoming = self._normalize(message, update)
                        if incoming:
                            await handler(incoming)

    def _normalize(self, message: dict, raw: dict) -> IncomingMessage | None:
        # Convierte un mensaje crudo de Telegram a IncomingMessage normalizado.
        # Ignora mensajes sin texto ni archivos reconocidos (ej: stickers, ubicaciones).
        text = message.get("text") or message.get("caption")
        attachments = self._extract_attachments(message)

        if not text and not attachments:
            return None

        return IncomingMessage(
            provider="telegram",
            chat_id=str(message["chat"]["id"]),
            user_id=str(message["from"]["id"]),
            text=text,
            attachments=attachments,
            raw=raw,
        )

    def _extract_attachments(self, message: dict) -> list[Attachment]:
        # Mapea los tipos de archivo de Telegram a la estructura genérica Attachment.
        attachments = []

        if "photo" in message:
            # Telegram devuelve la foto en múltiples resoluciones — tomamos la mayor.
            photo = max(message["photo"], key=lambda p: p["file_size"])
            attachments.append(Attachment(
                type="image",
                file_id=photo["file_id"],
                url=None,
                mime_type="image/jpeg",
                file_name=None,
            ))

        if "document" in message:
            doc = message["document"]
            attachments.append(Attachment(
                type="document",
                file_id=doc["file_id"],
                url=None,
                mime_type=doc.get("mime_type"),
                file_name=doc.get("file_name"),
            ))

        if "audio" in message:
            audio = message["audio"]
            attachments.append(Attachment(
                type="audio",
                file_id=audio["file_id"],
                url=None,
                mime_type=audio.get("mime_type"),
                file_name=audio.get("file_name"),
            ))

        if "voice" in message:
            attachments.append(Attachment(
                type="voice",
                file_id=message["voice"]["file_id"],
                url=None,
                mime_type="audio/ogg",
                file_name=None,
            ))

        if "video" in message:
            video = message["video"]
            attachments.append(Attachment(
                type="video",
                file_id=video["file_id"],
                url=None,
                mime_type=video.get("mime_type"),
                file_name=video.get("file_name"),
            ))

        return attachments

    async def _register_webhook(self) -> None:
        full_url = f"{self._webhook_url}{self._webhook_path}"
        async with httpx.AsyncClient() as client:
            await client.post(f"{self._base_url}/setWebhook", json={"url": full_url})
