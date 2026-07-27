import json
from datetime import date

from core.agents.base import Agent, AgentResult
from core.intents import Intent
from core.llm.base import LLMProvider
from core.messaging.base import IncomingMessage
from agents.financial.operations import FinancialOperations, OperationError
from agents.financial.prompt import SYSTEM_PROMPT_TEMPLATE


class FinancialAgent(Agent):
    # Implementación del contrato Agent para el dominio financiero.
    # Mismo patrón que el orquestador, un nivel más abajo: su LLM decide
    # qué operación ejecutar y las operaciones validan antes de tocar la base.

    name = "financial"
    description = description = (
        "Maneja las finanzas de la empresa: crea cuentas, registra gastos e ingresos "
        "(previstos y efectuados, con conciliación de facturas cobradas), consulta "
        "cuentas y pendientes, y genera el resumen mensual con ingresos, egresos, "
        "ganancia neta y división por socio."
    )

    def __init__(self, llm: LLMProvider, operations: FinancialOperations, max_iterations: int = 5):
        self._llm = llm
        self._max_iterations = max_iterations
        # Lista blanca: el LLM solo puede invocar lo que está registrado acá.
        # Cualquier otra cosa que se le ocurra, no existe para este agente.
        self._operations = {
            "crear_cuenta": operations.crear_cuenta,
            "listar_cuentas": operations.listar_cuentas,
            "registrar_egreso": operations.registrar_egreso,
            "registrar_ingreso_previsto": operations.registrar_ingreso_previsto,
            "listar_ingresos_previstos": operations.listar_ingresos_previstos,
            "registrar_ingreso_efectuado": operations.registrar_ingreso_efectuado,
            "resumen_mensual": operations.resumen_mensual,
        }

    async def handle(self, message: IncomingMessage, intent: Intent, instruction: str) -> AgentResult:
        # La fecha de hoy se inyecta en cada llamada para que el LLM resuelva
        # bien las fechas relativas ("ayer", "fin de mes").
        history = [
            {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(fecha_hoy=date.today().isoformat())},
            {"role": "user", "content": (
                f"Instrucción del orquestador: {instruction}\n"
                f"Mensaje original del usuario: {message.text}"
            )},
        ]

        # Mini loop agéntico, igual que el del orquestador: decidir → ejecutar
        # → ver resultado → decidir de nuevo, con límite de vueltas.
        for _ in range(self._max_iterations):
            response = self._llm.chat(history)
            decision = self._parse(response)
            print(f"[DEBUG financial] Decisión: {decision}")
            

            if decision is None:
                return AgentResult(text="No pude interpretar la instrucción recibida.", success=False)

            if decision.get("action") == "respond":
                return AgentResult(text=decision.get("text", ""))

            elif decision.get("action") == "execute":
                result_text = self._execute(decision)
                history.append({"role": "assistant", "content": response})
                history.append({"role": "user", "content": result_text})

            else:
                # Formato desconocido: avisarle al LLM en vez de repetir la
                # misma pregunta — sin este feedback, reintenta el mismo error.
                history.append({"role": "assistant", "content": response})
                history.append({"role": "user", "content": (
                    'Formato inválido. Respondé únicamente {"action": "execute", '
                    '"operation": "...", "args": {...}} o {"action": "respond", "text": "..."}.'
                )})

        return AgentResult(text="La instrucción requirió demasiados pasos y no pude completarla.", success=False)

    def _execute(self, decision: dict) -> str:
        # Ejecuta la operación elegida por el LLM, conteniendo todos los errores:
        # el loop siempre recibe texto, nunca una excepción sin manejar.
        op_name = decision.get("operation", "")
        op = self._operations.get(op_name)
        if op is None:
            return f"Error: la operación '{op_name}' no existe."

        args = decision.get("args") or {}
        try:
            result = op(**args)
        except OperationError as e:
            # Error de validación: el mensaje está pensado para el usuario.
            return f"Error de validación: {e}"
        except TypeError as e:
            # El LLM mandó argumentos que no coinciden con la firma de la función.
            return f"Error en los argumentos de {op_name}: {e}"

        # default=str convierte fechas y otros tipos no serializables a texto.
        return f"[Resultado de {op_name}]: {json.dumps(result, ensure_ascii=False, default=str)}"

    def _parse(self, response: str) -> dict | None:
        # Mismo saneo que en el orquestador: limpiar posible envoltorio markdown.
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").removeprefix("json").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None