import json
import logging
from datetime import date

from core.agents.base import Agent, AgentResult
from core.intents import Intent
from core.llm.base import LLMProvider
from core.messaging.base import IncomingMessage
from tools.reads.financial import FinancialReadTools
from reports.financial import FinancialReports
from agents.financial.prompt import SYSTEM_PROMPT

# El módulo pide su logger; a dónde va la salida lo decide main.py.
logger = logging.getLogger(__name__)


class FinancialAgent(Agent):
    # Agente financiero, por ahora de SOLO LECTURA. Cumple el contrato Agent para
    # que el orquestador lo pueda llamar igual que a cualquier sub-agente. Su caja
    # de herramientas son SOLO tools de lectura inyectadas — no puede escribir.

    name = "financial"
    description = (
        "Agente financiero de solo lectura. Consulta cuentas, ingresos y egresos "
        "(previstos y efectuados), y calcula el resultado de un mes separado "
        "por moneda. No modifica nada en la base."
    )

    def __init__(
        self,
        llm: LLMProvider,
        tools: FinancialReadTools,
        reports: FinancialReports,
        max_iterations: int = 5,
    ):
        self._llm = llm
        self._max_iterations = max_iterations
        self._reports = reports
        # Lista blanca: el LLM solo puede invocar lo que está registrado acá.
        # Todas son de lectura — por diseño, este agente no tiene ninguna
        # herramienta que escriba.
        self._tools = {
            "buscar_cuentas": tools.buscar_cuentas,
            "listar_ingresos_previstos": tools.listar_ingresos_previstos,
            "listar_egresos_previstos": tools.listar_egresos_previstos,
            "listar_ingresos_efectuados": tools.listar_ingresos_efectuados,
            "listar_egresos_efectuados": tools.listar_egresos_efectuados,
            # Un reporte devuelve números ya calculados; una tool devuelve datos
            # crudos. Conviven en la misma whitelist porque para el LLM son lo
            # mismo: algo que puede pedir. Y las dos son de solo lectura, así que
            # el protocolo {"action": "read"} sirve igual para ambas.
            "resultado_mensual_por_moneda": reports.resultado_mensual_por_moneda,
        }

    async def handle(self, message: IncomingMessage, intent: Intent, instruction: str) -> AgentResult:
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

        # Mini loop agéntico: decidir → leer → ver resultado → decidir de nuevo,
        # con límite de vueltas para no ciclar infinito.
        for _ in range(self._max_iterations):
            response = await self._llm.chat(history)
            decision = self._parse(response)
            logger.debug("financial decidió: %s", decision)

            if decision is None:
                return AgentResult(text="No pude interpretar la instrucción recibida.", success=False)

            if decision.get("action") == "respond":
                logger.debug("financial respondió: %s", decision.get("text", ""))
                return AgentResult(text=decision.get("text", ""))

            elif decision.get("action") == "read":
                result_text = self._read(decision)
                logger.debug("financial leyó: %s", result_text)
                history.append({"role": "assistant", "content": response})
                history.append({"role": "user", "content": result_text})

            else:
                # Formato desconocido: avisarle al LLM en vez de repetir el error.
                history.append({"role": "assistant", "content": response})
                history.append({"role": "user", "content": (
                    'Formato inválido. Respondé únicamente {"action": "read", '
                    '"tool": "...", "args": {...}} o {"action": "respond", "text": "..."}.'
                )})

        return AgentResult(text="La consulta requirió demasiados pasos y no pude completarla.", success=False)

    def _read(self, decision: dict) -> str:
        # Ejecuta la tool de lectura elegida por el LLM, conteniendo errores:
        # el loop siempre recibe texto, nunca una excepción sin manejar.
        tool_name = decision.get("tool", "")
        tool = self._tools.get(tool_name)
        if tool is None:
            return f"Error: la tool '{tool_name}' no existe."

        args = decision.get("args") or {}
        try:
            result = tool(**args)
        except TypeError as e:
            # El LLM mandó argumentos que no coinciden con la firma de la tool.
            return f"Error en los argumentos de {tool_name}: {e}"

        # default=str convierte fechas y otros tipos no serializables a texto.
        return f"[Resultado de {tool_name}]: {json.dumps(result, ensure_ascii=False, default=str)}"

    def _parse(self, response: str) -> dict | None:
        # Limpia un posible envoltorio markdown (```json ... ```) antes de parsear.
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").removeprefix("json").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None
