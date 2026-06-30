from abc import ABC, abstractmethod
from io import BytesIO


class VisionProvider(ABC):
    # Interfaz genérica para cualquier servicio de análisis de imágenes.
    # El Preprocessor depende de esta abstracción, nunca de Claude directamente.
    #
    # Para agregar un nuevo provider (ej: GPT-4V, Gemini Vision):
    #   1. Crear providers/vision/<nombre>.py
    #   2. Implementar esta clase: describe()
    #   3. Registrarlo en core/vision/factory.py
    #   4. Agregar VISION_PROVIDER=<nombre> al .env

    @abstractmethod
    async def describe(self, image: BytesIO, mime_type: str) -> str:
        # Recibe los bytes de la imagen y su mime_type, y devuelve una descripción textual.
        # Si es un documento financiero, extrae los datos relevantes (montos, fechas, conceptos).
        # El BytesIO se destruye al salir del scope del caller — no persiste en disco.
        pass
