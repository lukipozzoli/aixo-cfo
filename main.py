import asyncio
from core.messaging.base import IncomingMessage
from core.intents import Intent
from core.llm.factory import build_llm_provider
from core.transcription.factory import build_transcription_provider
from core.vision.factory import build_vision_provider
from core.preprocessing.preprocessor import Preprocessor
from agents.router import Router
from messaging.client import get_client
from config.aixo import (
    ROUTER_PROVIDER, ROUTER_MODEL,
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


async def handle(message: IncomingMessage) -> None:
    # Pipeline: Preprocessor → Router → Agente correspondiente.
    message = await _preprocessor.process(message)
    intent = _router.classify(message)

    # TODO: reemplazar cada rama por la llamada al agente correspondiente.
    match intent:
        case Intent.CONSULTA_INFORMACION:
            await _messaging.send(message.chat_id, f"[Financial Agent] Intent: {intent}")
        case Intent.CONSULTA_ARCHIVO:
            await _messaging.send(message.chat_id, f"[Financial Agent] Intent: {intent}")
        case Intent.REPORTE:
            await _messaging.send(message.chat_id, f"[Report Agent] Intent: {intent}")
        case Intent.PROYECCION:
            await _messaging.send(message.chat_id, f"[Financial Agent] Intent: {intent}")
        case Intent.INVESTIGACION:
            await _messaging.send(message.chat_id, f"[Research Agent] Intent: {intent}")
        case Intent.CONCILIACION:
            await _messaging.send(message.chat_id, f"[Financial Agent] Intent: {intent}")
        case Intent.EDICION_DB:
            await _messaging.send(message.chat_id, f"[Financial Agent] Intent: {intent}")
        case Intent.CONFIGURACION_ALERTA:
            await _messaging.send(message.chat_id, f"[Alert Agent] Intent: {intent}")
        case Intent.EVENTO_EXTERNO:
            await _messaging.send(message.chat_id, f"[Alert Agent] Intent: {intent}")
        case Intent.RESPUESTA_AGENTE:
            await _messaging.send(message.chat_id, f"[Conversation Agent] Intent: {intent}")
        case Intent.CONVERSACIONAL:
            await _messaging.send(message.chat_id, f"[Conversation Agent] Intent: {intent}")
        case Intent.DESCONOCIDO:
            await _messaging.send(message.chat_id, "No entendí tu mensaje. ¿Podés reformularlo?")


async def main() -> None:
    print("Agente CFO iniciado. Escuchando mensajes...")
    await _messaging.listen(handle)


if __name__ == "__main__":
    asyncio.run(main())
