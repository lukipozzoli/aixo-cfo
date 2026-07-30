from abc import ABC, abstractmethod
from typing import Any


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
