from abc import ABC, abstractmethod
from typing import Any


class LLMError(Exception):
    # Error de cualquier proveedor de LLM. Cada adapter envuelve acá las
    # excepciones de su SDK.
    #
    # Existe para que el core pueda atrapar una falla de LLM sin importar el SDK
    # del proveedor: sin esto, un `except` afuera de providers/ tendría que
    # nombrar anthropic.APIError, openai.APIError y la de Gemini — o sea importar
    # los tres SDK y saber cuál está configurado. Eso rompe la independencia de
    # proveedor
    # Los adapters envuelven con `raise LLMError(...) from e`: el `from e`
    # encadena la excepción original, así el traceback sigue mostrando qué falló
    # de verdad y queda accesible en __cause__.
    pass

class LLMProvider(ABC):
    # Interfaz genérica para cualquier proveedor de LLM.
    # El core nunca importa un SDK directamente — siempre pasa por acá.
    # Los métodos son async porque una llamada a un LLM es una espera de red de
    # varios segundos. Si fueran sincrónicos bloquearían el event loop entero y
    # el proceso no podría atender nada más mientras tanto. Es el mismo criterio
    # que ya siguen VisionProvider y TranscriptionProvider.

    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        # Conversación multi-turno. Recibe una lista de mensajes en formato
        # {"role": "user/assistant", "content": "..."} y devuelve la respuesta.
        pass

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        # Completion de texto plano. Para casos donde no hace falta historial.
        pass
