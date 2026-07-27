import os
from dotenv import load_dotenv

load_dotenv()

# Configuración específica de AIXO.
# Todo lo que cambia entre empresas vive acá — el core no toca este archivo.
# Si una variable requerida falta en .env, falla ruidosamente. Sin defaults silenciosos.

DATABASE_PROVIDER: str = os.environ["DATABASE_PROVIDER"]
DATABASE_URL: str = os.environ["DATABASE_URL"]
DATABASE_KEY: str = os.environ["DATABASE_KEY"]

# API keys de LLM — solo se requiere la del provider que use cada agente.
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# Cada agente elige su propio provider y modelo de forma independiente.
FINANCIAL_AGENT_PROVIDER: str = os.environ["FINANCIAL_AGENT_PROVIDER"]
FINANCIAL_AGENT_MODEL: str = os.environ["FINANCIAL_AGENT_MODEL"]

# Tester Agent — agente de solo lectura para pruebas.
TESTER_AGENT_PROVIDER: str = os.environ["TESTER_AGENT_PROVIDER"]
TESTER_AGENT_MODEL: str = os.environ["TESTER_AGENT_MODEL"]

CONVERSATION_AGENT_PROVIDER: str = os.environ["CONVERSATION_AGENT_PROVIDER"]
CONVERSATION_AGENT_MODEL: str = os.environ["CONVERSATION_AGENT_MODEL"]

REPORT_AGENT_PROVIDER: str = os.environ["REPORT_AGENT_PROVIDER"]
REPORT_AGENT_MODEL: str = os.environ["REPORT_AGENT_MODEL"]

ROUTER_PROVIDER: str = os.environ["ROUTER_PROVIDER"]
ROUTER_MODEL: str = os.environ["ROUTER_MODEL"]

# El Orquestador decide qué sub-agente resuelve cada mensaje.
ORCHESTRATOR_PROVIDER: str = os.environ["ORCHESTRATOR_PROVIDER"]
ORCHESTRATOR_MODEL: str = os.environ["ORCHESTRATOR_MODEL"]

# Mensajería
MESSAGING_PROVIDER: str = os.environ["MESSAGING_PROVIDER"]
MESSAGING_MODE: str = os.environ["MESSAGING_MODE"]
MESSAGING_PORT: int = int(os.environ["MESSAGING_PORT"])

# Variables específicas de Telegram — solo aplican si MESSAGING_PROVIDER=telegram.
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]
TELEGRAM_WEBHOOK_URL: str | None = os.getenv("TELEGRAM_WEBHOOK_URL")
TELEGRAM_WEBHOOK_PATH: str = os.environ["TELEGRAM_WEBHOOK_PATH"]

# Transcripción de audio
TRANSCRIPTION_PROVIDER: str = os.environ["TRANSCRIPTION_PROVIDER"]
TRANSCRIPTION_MODEL: str = os.environ["TRANSCRIPTION_MODEL"]

# Visión — análisis de imágenes y documentos visuales
VISION_PROVIDER: str = os.environ["VISION_PROVIDER"]
VISION_MODEL: str = os.environ["VISION_MODEL"]


def get_llm_api_key(provider: str) -> str:
    # Devuelve la API key correspondiente al provider indicado.
    # Falla ruidosamente si la key no está configurada en .env —
    # mejor un error claro al inicio que un fallo silencioso más adelante.
    mapping: dict[str, str | None] = {
        "claude": ANTHROPIC_API_KEY,
        "openai": OPENAI_API_KEY,
        "gemini": GEMINI_API_KEY,
    }
    key = mapping.get(provider)
    if not key:
        raise ValueError(f"API key no configurada para provider '{provider}'. Verificar .env.")
    return key
