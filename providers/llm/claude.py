import anthropic
from core.llm.base import LLMProvider


class ClaudeProvider(LLMProvider):
    # Implementación de LLMProvider usando la API de Anthropic.
    # El modelo y los parámetros se configuran por empresa, nunca hardcodeados acá.

    def __init__(self, api_key: str, model: str, max_tokens: int = 1024):
        # Recibe config desde afuera — este provider no sabe nada de AIXO.
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    async def chat(self, messages: list[dict], **kwargs) -> str:
        # Filtra el system prompt si viene en el primer mensaje con role "system",
        # porque la API de Anthropic lo recibe como parámetro separado.
        system = None
        filtered = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered.append(msg)

        params = {
            "model": self._model,
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "messages": filtered,
        }
        if system:
            params["system"] = system

        response = await self._client.messages.create(**params)
        return response.content[0].text

    async def complete(self, prompt: str, **kwargs) -> str:
        # Envuelve el prompt como un mensaje de usuario para reutilizar chat().
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)
