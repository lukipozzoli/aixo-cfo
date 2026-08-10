from datetime import date
from decimal import Decimal

from agents.orchestrator import Orchestrator
from core.agents.base import AgentResult


def test_format_result_serializa_tipos_no_nativos():
    # El orquestador arma con esto el texto que ve el LLM. Si un agente devuelve
    # un Decimal (la regla del proyecto para dinero) o un date dentro de `data`,
    # json.dumps sin default=str tira TypeError y se lleva puesto el pipeline.
    # Este test fija que no pueda volver a pasar.
    orquestador = Orchestrator(llm=None, agents=[])

    resultado = AgentResult(text="julio cerró bien", data={
        "resultado": Decimal("3019500.00"),
        "fecha": date(2026, 7, 31),
    })

    texto = orquestador._format_result("financial", resultado)

    # El Decimal viaja como string, no como float: str preserva la exactitud
    # (3019500.00), float la perdería (3019500.1).
    assert '"resultado": "3019500.00"' in texto
    assert '"fecha": "2026-07-31"' in texto