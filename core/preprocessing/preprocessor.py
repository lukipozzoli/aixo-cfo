from core.messaging.base import MessagingProvider, IncomingMessage
from core.transcription.base import TranscriptionProvider
from core.vision.base import VisionProvider


class Preprocessor:
    # Capa entre el proveedor de mensajería y el Router.
    # Descarga archivos adjuntos, los procesa según su tipo, y enriquece el texto
    # del IncomingMessage para que el Router siempre reciba texto clasificable.
    #
    # Ciclo de vida de los archivos:
    #   1. Se descarga en memoria (BytesIO) — nunca toca el disco.
    #   2. Se procesa (transcripción o descripción visual).
    #   3. El BytesIO sale del scope y Python lo libera automáticamente.
    #   4. La URL pública del archivo queda en Attachment.url para uso posterior
    #      (el Financial Agent la escribe en el campo comprobante de la DB si corresponde).

    def __init__(
        self,
        messaging: MessagingProvider,
        transcription: TranscriptionProvider,
        vision: VisionProvider,
    ):
        self._messaging = messaging
        self._transcription = transcription
        self._vision = vision

    async def process(self, message: IncomingMessage) -> IncomingMessage:
        if not message.attachments:
            return message

        text_parts = [message.text] if message.text else []

        for attachment in message.attachments:
            # Descarga los bytes en memoria y obtiene la URL pública del archivo.
            # La URL se guarda en el attachment para que esté disponible después del procesamiento.
            file_bytes, public_url = await self._messaging.download(attachment)
            attachment.url = public_url

            if attachment.type in ("audio", "voice"):
                transcript = await self._transcription.transcribe(file_bytes)
                text_parts.append(f"[Audio transcripto: {transcript}]")

            elif attachment.type == "image":
                mime = attachment.mime_type or "image/jpeg"
                description = await self._vision.describe(file_bytes, mime)
                text_parts.append(f"[Imagen analizada: {description}]")

            # Los documentos se dejan sin procesar por ahora — la URL queda disponible
            # para que el agente correspondiente los maneje según el intent clasificado.

        return IncomingMessage(
            provider=message.provider,
            chat_id=message.chat_id,
            user_id=message.user_id,
            text="\n".join(text_parts) if text_parts else None,
            attachments=message.attachments,
            raw=message.raw,
        )
