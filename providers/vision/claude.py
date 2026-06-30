import base64
from io import BytesIO
from anthropic import AsyncAnthropic
from core.vision.base import VisionProvider


VISION_PROMPT = """Analizá el contenido de esta imagen.
Si es un comprobante, factura, transferencia o cualquier documento financiero,
extraé los datos relevantes: montos, fechas, conceptos, partes involucradas (emisor/receptor).
Si no es un documento financiero, describí brevemente lo que ves."""


class ClaudeVisionProvider(VisionProvider):
    # Implementación de VisionProvider usando Claude con capacidad de visión.
    # Recibe config desde afuera — este provider no sabe nada de AIXO.

    def __init__(self, api_key: str, model: str):
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def describe(self, image: BytesIO, mime_type: str) -> str:
        # Codifica la imagen en base64 para enviarla a la API de Anthropic.
        # El BytesIO se lee una sola vez y no se persiste en ningún lado.
        image_data = base64.standard_b64encode(image.read()).decode("utf-8")

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": VISION_PROMPT,
                    },
                ],
            }],
        )
        return response.content[0].text
