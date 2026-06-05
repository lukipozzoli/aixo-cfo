from core.llm.base import LLMProvider


def build_llm_provider(provider: str, model: str, api_key: str, max_tokens: int = 1024) -> LLMProvider:
    # Factory que devuelve el LLMProvider correcto según el nombre del proveedor.
    # Los agentes llaman a esta función con su config — nunca importan un provider directamente.
    if provider == "claude":
        from providers.llm.claude import ClaudeProvider
        return ClaudeProvider(api_key=api_key, model=model, max_tokens=max_tokens)
    elif provider == "openai":
        from providers.llm.openai import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=model, max_tokens=max_tokens)
    elif provider == "gemini":
        from providers.llm.gemini import GeminiProvider
        return GeminiProvider(api_key=api_key, model=model, max_tokens=max_tokens)
    else:
        raise ValueError(f"Provider desconocido: '{provider}'. Opciones válidas: claude, openai, gemini.")
