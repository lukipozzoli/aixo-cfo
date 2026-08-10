import json

from core.llm.base import LLMProvider
from core.messaging.base import IncomingMessage
from core.intents import Intent
from core.agents.base import Agent, AgentResult


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


class Orchestrator:
    # Recibe el mensaje ya clasificado por el Router y decide cómo resolverlo:
    # a qué sub-agente llamar, con qué instrucción, y si encadenar varios.
    # Depende solo de las abstracciones LLMProvider y Agent — nunca de
    # implementaciones concretas (principio D de SOLID).

    def __init__(self, llm: LLMProvider, agents: list[Agent], max_iterations: int = 5):
        self._llm = llm
        # Registro de agentes por nombre. Agregar un agente nuevo es solo
        # sumarlo a la lista en main.py — esta clase no se modifica (principio O).
        self._agents = {agent.name: agent for agent in agents}
        # Límite de vueltas del loop para que un error de razonamiento
        # del LLM nunca deje al sistema ciclando (y gastando tokens) infinitamente.
        self._max_iterations = max_iterations

    async def run(self, message: IncomingMessage, intent: Intent) -> str:
        # El historial arranca con el prompt del sistema y el pedido del usuario,
        # y va acumulando las decisiones del LLM y los resultados de cada agente.
        # Así el LLM siempre decide con el contexto completo de lo que ya pasó.
        history = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": f"Intent del Router: {intent.value}\nMensaje del usuario: {message.text}"},
        ]

        for _ in range(self._max_iterations):
            response = await self._llm.chat(history)
            decision = self._parse_decision(response)
            print(f"[DEBUG] Decisión del LLM: {decision}")

            # Si el LLM devolvió algo no parseable, se corta acá con un
            # mensaje honesto en vez de arriesgar un comportamiento indefinido.
            if decision is None:
                return "No pude procesar tu pedido correctamente. ¿Podés reformularlo?"

            if decision.get("action") == "respond":
                return decision.get("text", "")

            if decision.get("action") == "call_agent":
                agent_name = decision.get("agent", "")
                agent = self._agents.get(agent_name)

                # El LLM puede alucinar un agente inexistente — se le informa
                # dentro del loop para que corrija en el próximo turno.
                if agent is None:
                    result_text = f"Error: el agente '{agent_name}' no existe."
                else:
                    result = await agent.handle(
                        message=message,
                        intent=intent,
                        instruction=decision.get("instruction", ""),
                    )
                    result_text = self._format_result(agent_name, result)
                    print(f"[DEBUG] Resultado del agente: {result_text}")

                # La decisión del LLM y el resultado del agente se agregan al
                # historial para que el próximo turno decida con esa información.
                history.append({"role": "assistant", "content": response})
                history.append({"role": "user", "content": result_text})

        # Se agotaron las iteraciones sin un "respond" — mejor avisar que colgarse.
        return "Tu pedido requirió demasiados pasos y no pude completarlo. ¿Podés dividirlo en partes?"

    def _build_system_prompt(self) -> str:
        # Arma el catálogo de agentes dinámicamente desde el registro.
        # El prompt siempre refleja los agentes realmente disponibles.
        catalog = "\n".join(
            f"- {agent.name}: {agent.description}" for agent in self._agents.values()
        )
        return SYSTEM_PROMPT_TEMPLATE.format(agents_catalog=catalog)

    def _parse_decision(self, response: str) -> dict | None:
        # Los LLMs a veces envuelven el JSON en un bloque de código markdown
        # (```json ... ```) aunque se les pida que no — se limpia antes de parsear.
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").removeprefix("json").strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    def _format_result(self, agent_name: str, result: AgentResult) -> str:
        # Convierte el AgentResult en texto plano para el historial del LLM.
        # Incluye data para que el próximo agente pueda usar esos valores.
        status = "OK" if result.success else "FALLÓ"
        text = f"[Resultado de {agent_name}] ({status}): {result.text}"
        if result.data:
            text += f"\nDatos: {json.dumps(result.data, ensure_ascii=False, default=str)}"
        return text