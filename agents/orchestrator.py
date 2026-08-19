import json

from core.llm.base import LLMProvider
from core.messaging.base import IncomingMessage
from core.intents import Intent
from core.agents.base import Agent, AgentResult
from core.agents.loop import AgentLoop, LoopMessages


SYSTEM_PROMPT_TEMPLATE = """Sos el Orquestador de un sistema de gestión financiera para una empresa.
Recibís un mensaje del usuario ya clasificado con un intent, y tenés que resolverlo
usando los agentes disponibles. Podés llamar a varios agentes en secuencia si hace falta.

Agentes disponibles:
{agents_catalog}

En cada turno respondé ÚNICAMENTE con un JSON válido, sin texto adicional, en uno de estos dos formatos:

1. Para llamar a un agente:
{{"action": "call_agent", "agent": "<nombre>", "instruction": "<orden específica para ese agente>"}}

2. Para responder al usuario y terminar:
{{"action": "respond", "text": "<respuesta final para el usuario>"}}

Reglas:
- El intent es una pista del Router, no una orden. Usá tu criterio.
- Llamá a un solo agente por turno. Vas a recibir su resultado antes de decidir el próximo paso.
- Si un agente falla, no reintentes infinitamente: informale el problema al usuario.
- Si el mensaje no requiere ningún agente (ej: un saludo), respondé directo.
"""

# Los textos del loop de ESTE orquestador. Los dos primeros los lee el usuario
# final, así que son los mismos de siempre. El tercero solo lo ve el LLM cuando
# eligió una acción que no existe.
MENSAJES = LoopMessages(
    parseo_fallido="No pude procesar tu pedido correctamente. ¿Podés reformularlo?",
    iteraciones_agotadas=(
        "Tu pedido requirió demasiados pasos y no pude completarlo. ¿Podés dividirlo en partes?"
    ),
    formato_invalido=(
        'Formato inválido. Respondé únicamente {"action": "call_agent", '
        '"agent": "...", "instruction": "..."} o {"action": "respond", "text": "..."}.'
    ),
)


class Orchestrator:
    # Recibe el mensaje ya clasificado por el Router y decide cómo resolverlo:
    # a qué sub-agente llamar, con qué instrucción, y si encadenar varios.
    # Depende solo de las abstracciones LLMProvider y Agent — nunca de
    # implementaciones concretas (principio D de SOLID).
    #
    # La mecánica de decidir → ejecutar → realimentar vive en AgentLoop. Acá
    # queda únicamente lo que es propio del orquestador: qué acción entiende
    # ("call_agent") y qué hace con ella.

    def __init__(self, llm: LLMProvider, agents: list[Agent], max_iterations: int = 5):
        self._llm = llm
        # Registro de agentes por nombre. Agregar un agente nuevo es solo
        # sumarlo a la lista en main.py — esta clase no se modifica (principio O).
        self._agents = {agent.name: agent for agent in agents}
        # Se le pasa al loop, que es quien corta cuando se agotan las vueltas.
        self._max_iterations = max_iterations

    async def run(self, message: IncomingMessage, intent: Intent) -> str:
        # El catálogo se arma acá adentro y no en el constructor porque la acción
        # necesita el mensaje y el intent de ESTA corrida. main.py procesa varios
        # mensajes en paralelo: guardarlos en self los mezclaría entre sí.
        async def call_agent(decision: dict) -> str:
            return await self._call_agent(decision, message, intent)

        loop = AgentLoop(
            llm=self._llm,
            nombre="orquestador",
            acciones={"call_agent": call_agent},
            mensajes=MENSAJES,
            max_iterations=self._max_iterations,
        )

        # El historial arranca con el prompt del sistema y el pedido del usuario;
        # el loop lo va llenando con las decisiones y los resultados de cada agente.
        history = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": f"Intent del Router: {intent.value}\nMensaje del usuario: {message.text}"},
        ]

        # El orquestador le habla al usuario, así que solo le interesa el texto:
        # el éxito o fracaso ya viaja adentro del mensaje que se le devuelve.
        outcome = await loop.run(history)
        return outcome.text

    async def _call_agent(self, decision: dict, message: IncomingMessage, intent: Intent) -> str:
        # Ejecuta la acción "call_agent": busca el agente en el registro, lo llama
        # y devuelve su resultado como texto para el historial del loop.
        agent_name = decision.get("agent", "")
        agent = self._agents.get(agent_name)

        # El LLM puede alucinar un agente inexistente — se le informa dentro del
        # loop para que corrija en el próximo turno.
        if agent is None:
            return f"Error: el agente '{agent_name}' no existe."

        result = await agent.handle(
            message=message,
            intent=intent,
            instruction=decision.get("instruction", ""),
        )
        return self._format_result(agent_name, result)

    def _build_system_prompt(self) -> str:
        # Arma el catálogo de agentes dinámicamente desde el registro.
        # El prompt siempre refleja los agentes realmente disponibles.
        catalog = "\n".join(
            f"- {agent.name}: {agent.description}" for agent in self._agents.values()
        )
        return SYSTEM_PROMPT_TEMPLATE.format(agents_catalog=catalog)

    def _format_result(self, agent_name: str, result: AgentResult) -> str:
        # Convierte el AgentResult en texto plano para el historial del LLM.
        # Incluye data para que el próximo agente pueda usar esos valores.
        status = "OK" if result.success else "FALLÓ"
        text = f"[Resultado de {agent_name}] ({status}): {result.text}"
        if result.data:
            text += f"\nDatos: {json.dumps(result.data, ensure_ascii=False, default=str)}"
        return text
