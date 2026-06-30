from core.transcription.base import TranscriptionProvider


def build_transcription_provider(provider: str, api_key: str, model: str) -> TranscriptionProvider:
    # Factory que devuelve el TranscriptionProvider correcto según configuración.
    if provider == "whisper":
        from providers.transcription.whisper import WhisperProvider
        return WhisperProvider(api_key=api_key, model=model)
    else:
        raise ValueError(f"Provider de transcripción desconocido: '{provider}'. Opciones válidas: whisper.")
