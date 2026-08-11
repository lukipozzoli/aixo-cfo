import asyncio
import logging
from core.messaging.base import IncomingMessage
from core.llm.factory import build_llm_provider
from core.transcription.factory import build_transcription_provider
from core.vision.factory import build_vision_provider
from core.preprocessing.preprocessor import Preprocessor
from agents.router import Router
from agents.orchestrator import Orchestrator
from agents.financial.agent import FinancialAgent
from tools.reads.financial import FinancialReadTools
from reports.financial import FinancialReports
from db.client import get_client as get_db_client
from messaging.client import get_client
from config.aixo import (
    ROUTER_PROVIDER, ROUTER_MODEL,
    ORCHESTRATOR_PROVIDER, ORCHESTRATOR_MODEL,
    FINANCIAL_AGENT_PROVIDER, FINANCIAL_AGENT_MODEL,
    TRANSCRIPTION_PROVIDER, TRANSCRIPTION_MODEL,
    VISION_PROVIDER, VISION_MODEL,
    LOG_LEVEL,
    get_llm_api_key,
)

# Configuración del logging: se hace UNA sola vez, acá en el composition root.
# Los módulos solo piden su logger y emiten; a dónde va la salida y con cuánto
# detalle se decide en un único lugar y se cambia por .env, sin tocar código.
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

# LOG_LEVEL se aplica SOLO a los módulos del proyecto; todo lo demás queda en
# WARNING. Es una lista blanca y no una lista negra a propósito: primero
# intentamos silenciar librería por librería y se escapó hpack, que en DEBUG
# imprime cada header HTTP/2 — incluida la apikey de Supabase en texto plano.
# Una lista de librerías a callar nunca está completa; una lista de módulos
# propios sí, porque son los nuestros.
for _modulo in ("__main__", "agents", "core", "reports", "tools", "providers", "db", "messaging"):
    logging.getLogger(_modulo).setLevel(LOG_LEVEL)

logger = logging.getLogger(__name__)

# Inicializa el Preprocessor con los providers configurados en .env.
_messaging = get_client()
_preprocessor = Preprocessor(
    messaging=_messaging,
    transcription=build_transcription_provider(
        provider=TRANSCRIPTION_PROVIDER,
        api_key=get_llm_api_key("openai"),  # Whisper usa la API de OpenAI
        model=TRANSCRIPTION_MODEL,
    ),
    vision=build_vision_provider(
        provider=VISION_PROVIDER,
        api_key=get_llm_api_key(VISION_PROVIDER),
        model=VISION_MODEL,
    ),
)

# Inicializa el Router con el provider y modelo configurados en .env.
_router = Router(
    llm=build_llm_provider(
        provider=ROUTER_PROVIDER,
        model=ROUTER_MODEL,
        api_key=get_llm_api_key(ROUTER_PROVIDER),
    )
)

# Un único cliente de base de datos, compartido por las tools y los reportes:
# los dos dependen de la misma abstracción, no hace falta una conexión por cada uno.
_db = get_db_client()

# Inicializa el Financial Agent: agente financiero, por ahora de solo lectura.
# Recibe las tools de lectura y los reportes ya armados (inyección desde acá).
_financial = FinancialAgent(
    llm=build_llm_provider(
        provider=FINANCIAL_AGENT_PROVIDER,
        model=FINANCIAL_AGENT_MODEL,
        api_key=get_llm_api_key(FINANCIAL_AGENT_PROVIDER),
    ),
    tools=FinancialReadTools(db=_db),
    reports=FinancialReports(db=_db),
)

# Inicializa el Orquestador con su LLM y los sub-agentes registrados.
# Para sumar un agente nuevo, solo se agrega a esta lista.
_orchestrator = Orchestrator(
    llm=build_llm_provider(
        provider=ORCHESTRATOR_PROVIDER,
        model=ORCHESTRATOR_MODEL,
        api_key=get_llm_api_key(ORCHESTRATOR_PROVIDER),
    ),
    agents=[_financial],
)

# Tareas en vuelo. asyncio guarda solo una referencia débil a cada tarea, así que
# sin este set el recolector de basura puede matar una a mitad de camino.
_tareas_en_vuelo: set[asyncio.Task] = set()


async def handle(message: IncomingMessage) -> None:
    # Pipeline: Preprocessor → Router → Orchestrator → send.
    #
    # El try/except vive acá para que un error termine en una respuesta al usuario
    # y no en un silencio. Antes una excepción se llevaba puesto el loop de
    # mensajería entero y el bot dejaba de atender a todos; ahora solo se cae
    # el mensaje que falló.
    try:
        message = await _preprocessor.process(message)
        intent = await _router.classify(message)
        response = await _orchestrator.run(message, intent)
        await _messaging.send(message.chat_id, response)
    except Exception:
        logger.exception("Falló el pipeline procesando un mensaje")
        await _messaging.send(
            message.chat_id,
            "Se me complicó procesando eso. Probá de nuevo en un momento.",
        )


def _reportar_error(tarea: asyncio.Task) -> None:
    # Red de seguridad por si algo se escapó del try/except de handle (por ejemplo,
    # que falle el propio send). Sin esto la excepción queda guardada adentro de la
    # tarea y no se entera nadie.
    if not tarea.cancelled() and tarea.exception() is not None:
        logger.error("Error no atrapado en una tarea", exc_info=tarea.exception())


async def dispatch(message: IncomingMessage) -> None:
    # Lanza el pipeline como tarea y vuelve enseguida, para que el proveedor de
    # mensajería pueda seguir recibiendo mientras este mensaje se procesa.
    #
    # Esta decisión vive acá y no adentro de un provider a propósito: procesar en
    # paralelo es una política de la aplicación, no un detalle del transporte. Si
    # la tomara cada provider por su cuenta, cambiar de mensajería cambiaría el
    # comportamiento además del canal — y la idea es que cambiar de proveedor sea
    # cambiar una variable del .env, nada más.
    tarea = asyncio.create_task(handle(message))
    _tareas_en_vuelo.add(tarea)
    tarea.add_done_callback(_tareas_en_vuelo.discard)
    tarea.add_done_callback(_reportar_error)

async def main() -> None:
    logger.info("Agente CFO iniciado. Escuchando mensajes...")
    await _messaging.listen(dispatch)


if __name__ == "__main__":
    asyncio.run(main())
