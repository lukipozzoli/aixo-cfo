from openai import AsyncOpenAI
from core.llm.base import LLMProvider, LLMError


class OpenAIProvider(LLMProvider):
    # Implementación de LLMProvider usando la API de OpenAI.
    # Recibe config desde afuera — este provider no sabe nada de AIXO.

    def __init__(self, api_key: str, model: str, max_tokens: int = 1024):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def chat(self, messages: list[dict], **kwargs) -> str:
        # La API de OpenAI acepta el system prompt como un mensaje más con role "system",
        # así que no hace falta separarlo como en Anthropic.
        # Se envuelve sólo la llamada al SDK y la lectura de su respuesta, no el
        # código propio. Mismo criterio que en claude.py.
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=kwargs.get("max_tokens", self._max_tokens),
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise LLMError(f"Falló la llamada a OpenAI: {e}") from e

    async def complete(self, prompt: str, **kwargs) -> str:
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)
