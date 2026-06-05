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

CONVERSATION_AGENT_PROVIDER: str = os.environ["CONVERSATION_AGENT_PROVIDER"]
CONVERSATION_AGENT_MODEL: str = os.environ["CONVERSATION_AGENT_MODEL"]

REPORT_AGENT_PROVIDER: str = os.environ["REPORT_AGENT_PROVIDER"]
REPORT_AGENT_MODEL: str = os.environ["REPORT_AGENT_MODEL"]

ROUTER_PROVIDER: str = os.environ["ROUTER_PROVIDER"]
ROUTER_MODEL: str = os.environ["ROUTER_MODEL"]

# Mensajería
MESSAGING_PROVIDER: str = os.environ["MESSAGING_PROVIDER"]
MESSAGING_MODE: str = os.environ["MESSAGING_MODE"]
MESSAGING_PORT: int = int(os.environ["MESSAGING_PORT"])

# Variables específicas de Telegram — solo aplican si MESSAGING_PROVIDER=telegram.
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str = os.environ["TELEGRAM_CHAT_ID"]
TELEGRAM_WEBHOOK_URL: str | None = os.getenv("TELEGRAM_WEBHOOK_URL")  # requerido en modo webhook
TELEGRAM_WEBHOOK_PATH: str = os.environ["TELEGRAM_WEBHOOK_PATH"]
