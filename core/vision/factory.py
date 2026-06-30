from core.vision.base import VisionProvider


def build_vision_provider(provider: str, api_key: str, model: str) -> VisionProvider:
    # Factory que devuelve el VisionProvider correcto según configuración.
    if provider == "claude":
        from providers.vision.claude import ClaudeVisionProvider
        return ClaudeVisionProvider(api_key=api_key, model=model)
    else:
        raise ValueError(f"Provider de visión desconocido: '{provider}'. Opciones válidas: claude.")
