from io import BytesIO
from openai import AsyncOpenAI
from core.transcription.base import TranscriptionProvider


class WhisperProvider(TranscriptionProvider):
    # Implementación de TranscriptionProvider usando Whisper de OpenAI.
    # Recibe config desde afuera — este provider no sabe nada de AIXO.

    def __init__(self, api_key: str, model: str):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def transcribe(self, audio: BytesIO) -> str:
        # La API de OpenAI necesita un nombre de archivo para detectar el formato.
        # Pasamos una tupla (nombre, bytes) en lugar de un BytesIO para evitar
        # tener que setear atributos en el objeto — BytesIO no los soporta nativamente.
        audio_bytes = audio.read()
        response = await self._client.audio.transcriptions.create(
            model=self._model,
            file=("audio.ogg", audio_bytes),
        )
        return response.text
