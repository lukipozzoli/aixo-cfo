from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Tool:
    # Contrato genérico de una herramienta: qué es, cómo se la nombra, y qué hace.
    # No sabe nada de finanzas —igual que Agent o LLMProvider— así que cualquier
    # agente futuro usa este mismo contrato sin copiar nada.
    #
    # Un agente recibe una lista de Tool y no las clases que las implementan: deja
    # de depender de FinancialReadTools o de cualquier otra concreta (principio D).
    #
    # frozen=True porque una tool no cambia después de armada. Si algo la muta a
    # mitad de una corrida, el LLM estaría pidiendo una cosa y ejecutándose otra.

    nombre: str        # el identificador que el LLM escribe en {"tool": "..."}
    argumentos: str    # la firma en texto, ej "mes?" — el LLM la lee, no la parsea
    descripcion: str   # qué hace y qué significa cada argumento, para el LLM
    ejecutar: Callable # el método que hace el trabajo, ya atado a su instancia