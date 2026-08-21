import json
from datetime import date

from core.agents.base import Agent, AgentResult
from core.agents.loop import AgentLoop, LoopMessages
from core.intents import Intent
from core.llm.base import LLMProvider
from core.messaging.base import IncomingMessage
from core.tools.base import Tool
from agents.financial.prompt import SYSTEM_PROMPT

# Los textos del loop de ESTE agente. Los dos primeros son los mismos de siempre;
# el tercero es el aviso de formato que ya tenía, movido acá sin cambiarle una coma.
MENSAJES = LoopMessages(
    parseo_fallido="No pude interpretar la instrucción recibida.",
    iteraciones_agotadas="La consulta requirió demasiados pasos y no pude completarla.",
    formato_invalido=(
        'Formato inválido. Respondé únicamente {"action": "read", '
        '"tool": "...", "args": {...}} o {"action": "respond", "text": "..."}.'
    ),
)


class FinancialAgent(Agent):
    # Agente financiero, por ahora de SOLO LECTURA. Cumple el contrato Agent para
    # que el orquestador lo pueda llamar igual que a cualquier sub-agente. Su caja
    # de herramientas son SOLO tools de lectura inyectadas — no puede escribir.
    #
    # La mecánica del loop vive en AgentLoop. Acá queda lo propio del agente: qué
    # acción entiende ("read"), qué tools tiene en su lista blanca, y cómo las
    # ejecuta.

    name = "financial"
    description = (
        "Agente financiero de solo lectura. Consulta cuentas, ingresos y egresos "
        "(previstos y efectuados), y calcula el resultado de un mes separado "
        "por moneda. No modifica nada en la base."
    )

    def __init__(
        self,
        llm: LLMProvider,
        tools: list[Tool],
        max_iterations: int = 5,
    ):
        self._llm = llm
        self._max_iterations = max_iterations
        # Lista blanca: el LLM solo puede invocar lo que está registrado acá. Las
        # tools llegan armadas desde main.py, así que este agente no conoce ninguna
        # implementación concreta — solo el contrato Tool (principio D de SOLID).
        #
        # Las de lectura y los reportes conviven en la misma lista porque para el
        # LLM son lo mismo: algo que puede pedir. La diferencia entre datos crudos
        # y números calculados importa del lado de quien los produce, no de acá.
        self._tools = {tool.nombre: tool for tool in tools}

    async def handle(self, message: IncomingMessage, intent: Intent, instruction: str) -> AgentResult:
        # El loop se arma por llamada, igual que en el orquestador, para que dos
        # mensajes procesados en paralelo no compartan estado.
        loop = AgentLoop(
            llm=self._llm,
            nombre="financial",
            acciones={"read": self._read},
            mensajes=MENSAJES,
            max_iterations=self._max_iterations,
        )

        history = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                # La fecha va explícita porque el LLM no tiene forma de saberla. Sin
                # esto, ante un "este mes" adivinaría el período — y un mes adivinado
                # devuelve datos de otro mes sin que nada avise.
                f"Fecha de hoy: {date.today().isoformat()}\n"
                f"Instrucción del orquestador: {instruction}\n"
                f"Mensaje original del usuario: {message.text}"
            )},
        ]

        # El agente le habla al orquestador, que sí necesita saber si funcionó:
        # por eso acá el success del loop se conserva en el AgentResult.
        outcome = await loop.run(history)
        return AgentResult(text=outcome.text, success=outcome.success)

    async def _read(self, decision: dict) -> str:
        # Ejecuta la tool de lectura elegida por el LLM, conteniendo errores:
        # el loop siempre recibe texto, nunca una excepción sin manejar.
        #
        # Es async porque el catálogo del loop lo exige; la tool de adentro sigue
        # siendo sincrónica, igual que antes (ver Pendientes: DatabaseClient).
        tool_name = decision.get("tool", "")
        tool = self._tools.get(tool_name)
        if tool is None:
            return f"Error: la tool '{tool_name}' no existe."

        args = decision.get("args") or {}
        try:
            result = tool.ejecutar(**args)
        except TypeError as e:
            # El LLM mandó argumentos que no coinciden con la firma de la tool.
            return f"Error en los argumentos de {tool_name}: {e}"

        # default=str convierte fechas y otros tipos no serializables a texto.
        return f"[Resultado de {tool_name}]: {json.dumps(result, ensure_ascii=False, default=str)}"
