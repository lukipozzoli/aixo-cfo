import asyncio
from core.messaging.base import IncomingMessage
from messaging.client import get_client


async def handle(message: IncomingMessage) -> None:
    # Handler de prueba — hace echo del mensaje recibido.
    # Se reemplaza por el Router cuando esté construido.
    messaging = get_client()
    response_parts = []

    if message.text:
        response_parts.append(f"Texto: {message.text}")

    for attachment in message.attachments:
        response_parts.append(f"Archivo recibido — tipo: {attachment.type}, nombre: {attachment.file_name or 'sin nombre'}")

    if response_parts:
        await messaging.send(message.chat_id, "\n".join(response_parts))


async def main() -> None:
    messaging = get_client()
    print("Agente CFO iniciado. Escuchando mensajes...")
    await messaging.listen(handle)


if __name__ == "__main__":
    asyncio.run(main())
