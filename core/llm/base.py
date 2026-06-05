from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    # Interfaz genérica para cualquier proveedor de LLM.
    # El core nunca importa un SDK directamente — siempre pasa por acá.

    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> str:
        # Conversación multi-turno. Recibe una lista de mensajes en formato
        # {"role": "user/assistant", "content": "..."} y devuelve la respuesta.
        pass

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        # Completion de texto plano. Para casos donde no hace falta historial.
        pass
