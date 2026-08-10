import google.generativeai as genai
from core.llm.base import LLMProvider, LLMError


class GeminiProvider(LLMProvider):
    # Implementación de LLMProvider usando la API de Google Gemini.
    # Recibe config desde afuera — este provider no sabe nada de AIXO.

    def __init__(self, api_key: str, model: str, max_tokens: int = 1024):
        genai.configure(api_key=api_key)
        self._model_name = model
        self._max_tokens = max_tokens

    async def chat(self, messages: list[dict], **kwargs) -> str:
        # Gemini separa el system prompt del historial de conversación.
        # El primer mensaje con role "system" se extrae y se pasa como system_instruction.
        system = None
        history = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            elif msg["role"] == "user":
                history.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                history.append({"role": "model", "parts": [msg["content"]]})

        # Todo este bloque es territorio del SDK de Google: construir el modelo,
        # abrir el chat y mandar el mensaje. Se envuelve entero.
        try:
            model = genai.GenerativeModel(
                model_name=self._model_name,
                system_instruction=system,
            )
            # El último mensaje del usuario se envía como el turno actual.
            # El historial previo se pasa en start_chat para mantener contexto.
            last_user_message = history[-1]["parts"][0] if history else ""
            chat = model.start_chat(history=history[:-1] if history else [])
            response = await chat.send_message_async(
                last_user_message,
                generation_config={"max_output_tokens": kwargs.get("max_tokens", self._max_tokens)},
            )
            return response.text
        except Exception as e:
            raise LLMError(f"Falló la llamada a Gemini: {e}") from e

    async def complete(self, prompt: str, **kwargs) -> str:
        return await self.chat([{"role": "user", "content": prompt}], **kwargs)
