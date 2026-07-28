import asyncio
from core.messaging.base import IncomingMessage
from core.llm.factory import build_llm_provider
from core.transcription.factory import build_transcription_provider
from core.vision.factory import build_vision_provider
from core.preprocessing.preprocessor import Preprocessor
from agents.router import Router
from agents.orchestrator import Orchestrator
from agents.financial.agent import FinancialAgent
from tools.reads.financial import FinancialReadTools
from db.client import get_client as get_db_client
from messaging.client import get_client
from config.aixo import (
    ROUTER_PROVIDER, ROUTER_MODEL,
    ORCHESTRATOR_PROVIDER, ORCHESTRATOR_MODEL,
    FINANCIAL_AGENT_PROVIDER, FINANCIAL_AGENT_MODEL,
    TRANSCRIPTION_PROVIDER, TRANSCRIPTION_MODEL,
    VISION_PROVIDER, VISION_MODEL,
    get_llm_api_key,
)

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


# Inicializa el Financial Agent: agente financiero, por ahora de solo lectura.
# Recibe las tools de lectura ya armadas (inyección desde acá).
_financial = FinancialAgent(
    llm=build_llm_provider(
        provider=FINANCIAL_AGENT_PROVIDER,
        model=FINANCIAL_AGENT_MODEL,
        api_key=get_llm_api_key(FINANCIAL_AGENT_PROVIDER),
    ),
    tools=FinancialReadTools(db=get_db_client()),
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

async def handle(message: IncomingMessage) -> None:
    # Pipeline: Preprocessor → Router → Orchestrator → send.
    message = await _preprocessor.process(message)
    intent = _router.classify(message)
    response = await _orchestrator.run(message, intent)
    await _messaging.send(message.chat_id, response)


async def main() -> None:
    print("Agente CFO iniciado. Escuchando mensajes...")
    await _messaging.listen(handle)


if __name__ == "__main__":
    asyncio.run(main())
