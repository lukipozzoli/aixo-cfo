from dotenv import load_dotenv

# load_dotenv() va acá arriba de todo y no en cada archivo de config.
#
# Python ejecuta este __init__.py antes que cualquier submódulo del paquete, así
# que para cuando database.py o messaging.py lean os.environ, las variables del
# .env ya están cargadas. Un solo lugar, y ninguno de los otros archivos tiene
# que acordarse de llamarlo.
load_dotenv()

# Los imports van DESPUÉS de load_dotenv() a propósito: si fueran antes, cada
# archivo intentaría leer variables que todavía no existen.
from config.agents import (  # noqa: E402
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    GEMINI_API_KEY,
    ROUTER_PROVIDER,
    ROUTER_MODEL,
    ORCHESTRATOR_PROVIDER,
    ORCHESTRATOR_MODEL,
    FINANCIAL_AGENT_PROVIDER,
    FINANCIAL_AGENT_MODEL,
    get_llm_api_key,
)
from config.database import (  # noqa: E402
    DATABASE_PROVIDER,
    DATABASE_CONFIG,
)
from config.media import (  # noqa: E402
    TRANSCRIPTION_PROVIDER,
    TRANSCRIPTION_MODEL,
    VISION_PROVIDER,
    VISION_MODEL,
)
from config.messaging import (  # noqa: E402
    MESSAGING_PROVIDER,
    MESSAGING_CONFIG,
    TELEGRAM_CHAT_ID,
)
