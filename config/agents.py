import os

# Qué modelo de IA usa cada agente, y con qué credenciales.

# Las API keys son opcionales (os.getenv devuelve None si faltan) porque solo
# hace falta la del proveedor que realmente se use. Si alguien configura todo
# con OpenAI, no tiene por qué tener una key de Anthropic.
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# Cada agente elige su proveedor y modelo por separado. Así se puede poner un
# modelo barato en las tareas simples (clasificar un mensaje) y uno caro solo
# donde hace falta razonar.
ROUTER_PROVIDER: str = os.environ["ROUTER_PROVIDER"]
ROUTER_MODEL: str = os.environ["ROUTER_MODEL"]

ORCHESTRATOR_PROVIDER: str = os.environ["ORCHESTRATOR_PROVIDER"]
ORCHESTRATOR_MODEL: str = os.environ["ORCHESTRATOR_MODEL"]

FINANCIAL_AGENT_PROVIDER: str = os.environ["FINANCIAL_AGENT_PROVIDER"]
FINANCIAL_AGENT_MODEL: str = os.environ["FINANCIAL_AGENT_MODEL"]

# El Conversation Agent y el Report Agent todavía no existen. Su configuración
# se agrega cuando se escriban, no antes: una variable obligatoria que no lee
# nadie solo sirve para frenar el arranque de quien no la puso.


def get_llm_api_key(provider: str) -> str:
    # Traduce el nombre del proveedor a su API key.
    # Falla ruidosamente si la key no está: mejor un error claro que descubrir
    # a mitad de una conversación que faltaba una credencial.
    mapping: dict[str, str | None] = {
        "claude": ANTHROPIC_API_KEY,
        "openai": OPENAI_API_KEY,
        "gemini": GEMINI_API_KEY,
    }
    key = mapping.get(provider)
    if not key:
        raise ValueError(f"API key no configurada para provider '{provider}'. Verificar .env.")
    return key
