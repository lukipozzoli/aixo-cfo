import json
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

from core.llm.base import LLMProvider

# El módulo pide su logger; a dónde va la salida lo decide main.py.
logger = logging.getLogger(__name__)


# Una acción recibe la decisión ya parseada y devuelve el texto que vuelve al
# historial. Es async porque ejecutarla puede ser una espera de red (llamar a
# otro agente que a su vez consulta un LLM); si fuera sincrónica bloquearía el
# event loop entero mientras dura.
Accion = Callable[[dict], Awaitable[str]]


@dataclass(frozen=True)
class LoopMessages:
    # Los tres textos que el loop necesita y que cambian según quién lo use.
    # Se inyectan en vez de vivir acá adentro porque el orquestador le habla al
    # usuario final y un sub-agente le habla al orquestador: mismo momento del
    # loop, distinto interlocutor y distinto tono.
    parseo_fallido: str        # al usuario: el LLM no devolvió un objeto JSON
    iteraciones_agotadas: str  # al usuario: se agotaron las vueltas sin respuesta
    formato_invalido: str      # al LLM: eligió una acción que no está en el catálogo


@dataclass
class LoopOutcome:
    # Resultado neutro del loop. No devuelve un AgentResult ni un str pelado a
    # propósito: el loop no sabe quién lo llama, así que entrega lo mínimo y cada
    # uno lo envuelve como le corresponde (principio I de SOLID — no imponerle a
    # un cliente una interfaz pensada para otro).
    text: str
    success: bool = True


class AgentLoop:
    # Loop agéntico acotado: preguntarle al LLM qué hacer, ejecutarlo, mostrarle
    # el resultado, y repetir hasta que responda o se acaben las vueltas.
    #
    # No conoce agentes ni tools: recibe el catálogo de acciones desde afuera
    # (principio D de SOLID). Lo único que sabe del protocolo es que "respond"
    # termina — y eso no es una acción de dominio, es su forma de cortar.

    def __init__(
        self,
        llm: LLMProvider,
        nombre: str,
        acciones: dict[str, Accion],
        mensajes: LoopMessages,
        max_iterations: int = 5,
    ):
        self._llm = llm
        # Solo para los logs: identifica de quién es este loop cuando hay varios
        # corriendo en paralelo por el dispatch concurrente de main.py.
        self._nombre = nombre
        # Lista blanca: el LLM solo puede invocar lo que está registrado acá.
        self._acciones = acciones
        self._mensajes = mensajes
        # Límite de vueltas para que un error de razonamiento del LLM nunca deje
        # al sistema ciclando (y gastando tokens) infinitamente.
        self._max_iterations = max_iterations

    async def run(self, history: list[dict]) -> LoopOutcome:
        # El historial llega ya armado por quien llama: el loop no construye
        # prompts. Acá adentro solo crece con lo que va pasando.
        for _ in range(self._max_iterations):
            response = await self._llm.chat(history)
            decision = self._parse(response)
            logger.debug("%s decidió: %s", self._nombre, decision)

            # Si el LLM no devolvió un objeto JSON se corta con un mensaje
            # honesto, en vez de arriesgar un comportamiento indefinido.
            if decision is None:
                return LoopOutcome(self._mensajes.parseo_fallido, success=False)

            if decision.get("action") == "respond":
                texto = decision.get("text", "")
                logger.debug("%s respondió: %s", self._nombre, texto)
                return LoopOutcome(texto)

            # Todo lo que no es "respond" sale del catálogo. El isinstance filtra
            # el caso de que "action" venga con algo que no sea texto (una lista,
            # por ejemplo), que como clave de diccionario reventaría.
            nombre_accion = decision.get("action")
            accion = self._acciones.get(nombre_accion) if isinstance(nombre_accion, str) else None

            # Acción inexistente: se le avisa DENTRO del loop para que corrija en
            # la próxima vuelta. Sin esto el historial no cambia, el LLM recibe el
            # mismo prompt de nuevo y repite el error hasta agotar las vueltas.
            if accion is None:
                result_text = self._mensajes.formato_invalido
            else:
                result_text = await accion(decision)
                logger.debug("%s ejecutó: %s", self._nombre, result_text)

            # La decisión del LLM y su resultado se agregan al historial para que
            # la próxima vuelta decida con esa información.
            history.append({"role": "assistant", "content": response})
            history.append({"role": "user", "content": result_text})

        # Se agotaron las vueltas sin un "respond" — mejor avisar que colgarse.
        return LoopOutcome(self._mensajes.iteraciones_agotadas, success=False)

    def _parse(self, response: str) -> dict | None:
        # Los LLMs a veces envuelven el JSON en un bloque de código markdown
        # (```json ... ```) aunque se les pida que no — se limpia antes de parsear.
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").removeprefix("json").strip()

        try:
            decision = json.loads(cleaned)
        except json.JSONDecodeError:
            return None

        # json.loads acepta listas, números y textos sueltos: '["read"]' parsea
        # perfecto y después decision.get() explota con AttributeError. Solo un
        # objeto sirve como decisión, así que lo demás se trata como no parseable.
        return decision if isinstance(decision, dict) else None
