from abc import ABC, abstractmethod
from io import BytesIO


class TranscriptionProvider(ABC):
    # Interfaz genérica para cualquier servicio de transcripción de audio a texto.
    # El Preprocessor depende de esta abstracción, nunca de Whisper directamente.
    #
    # Para agregar un nuevo provider (ej: Google Speech, Azure Speech):
    #   1. Crear providers/transcription/<nombre>.py
    #   2. Implementar esta clase: transcribe()
    #   3. Registrarlo en core/transcription/factory.py
    #   4. Agregar TRANSCRIPTION_PROVIDER=<nombre> al .env

    @abstractmethod
    async def transcribe(self, audio: BytesIO) -> str:
        # Recibe los bytes del archivo de audio y devuelve el texto transcripto.
        # El BytesIO se destruye al salir del scope del caller — no persiste en disco.
        pass
