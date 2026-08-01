from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from core.intents import Intent
from core.messaging.base import IncomingMessage


@dataclass
class AgentResult:
    # Resultado normalizado que devuelve cualquier sub-agente.
    # El orquestador lo usa para decidir si ya puede responder al usuario
    # o si necesita encadenar otro agente con esta información.
    text: str                                  # respuesta en lenguaje natural o resumen de lo hecho
    data: dict = field(default_factory=dict)   # datos estructurados para que otro agente los consuma
    success: bool = True                       # False si el agente no pudo completar su tarea


class Agent(ABC):
    # Contrato que todo sub-agente debe cumplir.
    # El orquestador depende únicamente de esta interfaz — nunca importa
    # un agente concreto. Agregar un sub-agente nuevo no requiere tocar
    # el orquestador: solo implementar esta clase y registrarlo en main.py.

    name: str          # identificador corto y único, ej: "financial", "arca"
    description: str   # qué sabe hacer, en lenguaje natural — el orquestador
                       # arma su prompt con las descripciones de todos los agentes

    @abstractmethod
    async def handle(self, message: IncomingMessage, intent: Intent, instruction: str) -> AgentResult:
        # message: el mensaje original ya preprocesado (siempre texto)
        # intent: la clasificación que hizo el Router
        # instruction: la orden específica que el orquestador le da a ESTE agente
        #   (puede diferir del mensaje original — ej: "registrá un egreso de 50 USD")
        pass