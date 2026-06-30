from core.llm.base import LLMProvider
from core.messaging.base import IncomingMessage
from core.intents import Intent


SYSTEM_PROMPT = """Sos el Router de un sistema de gestión financiera para una empresa.
Tu única tarea es clasificar el mensaje del usuario en exactamente uno de los siguientes intents:

- consulta_informacion: pregunta sobre un dato puntual (saldo, movimiento, estado de una cuenta, inversión, préstamo, etc.)
- consulta_archivo: pedido de un comprobante, factura o documento adjunto
- reporte: pedido de un resumen agregado o histórico (flujo del mes, balance, etc.)
- proyeccion: análisis de escenarios futuros basado en datos internos (caja en 30 días, renovación de plazo fijo, etc.)
- investigacion: análisis que requiere contexto externo (tipo de cambio, inflación, tendencias de mercado)
- conciliacion: cruce entre ingresos/egresos previstos y efectuados (qué está pendiente de cobrar o pagar)
- edicion_db: alta, modificación o eliminación de un registro (registrar un pago, agregar una cuenta, etc.)
- configuracion_alerta: configurar umbrales o notificaciones proactivas (avisame si el saldo baja de X)
- evento_externo: notificación de un evento predefinido que dispara lógica financiera
- respuesta_agente: el usuario está respondiendo una pregunta que el agente hizo previamente
- conversacional: mensaje sin intención financiera clara (saludo, charla general, agradecimiento)
- desconocido: no se puede clasificar con confianza en ninguna de las anteriores

Reglas:
- Respondé ÚNICAMENTE con el nombre del intent, sin explicaciones ni texto adicional.
- Si hay archivos adjuntos sin texto, clasificá según el tipo de archivo (un PDF probablemente sea consulta_archivo o edicion_db).
- Ante la duda, usá desconocido.
"""


class Router:
    # Clasifica mensajes entrantes en intents usando un LLM.
    # No tiene lógica de negocio — solo clasifica y delega.

    def __init__(self, llm: LLMProvider):
        self._llm = llm

    def classify(self, message: IncomingMessage) -> Intent:
        # Construye el contenido del mensaje para el LLM.
        # Si hay archivos adjuntos, los menciona explícitamente para ayudar a clasificar.
        content_parts = []

        if message.text:
            content_parts.append(message.text)

        if message.attachments:
            types = [f"{a.type} ({a.file_name or 'sin nombre'})" for a in message.attachments]
            content_parts.append(f"[Archivos adjuntos: {', '.join(types)}]")

        user_content = "\n".join(content_parts).strip()

        response = self._llm.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ])

        # Valida que la respuesta sea un intent conocido.
        # Si el LLM alucina o responde algo inesperado, cae en desconocido.
        intent_str = response.strip().lower()
        try:
            return Intent(intent_str)
        except ValueError:
            return Intent.DESCONOCIDO
