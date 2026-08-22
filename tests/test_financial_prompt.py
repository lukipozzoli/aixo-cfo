from core.tools.base import Tool
from agents.financial.agent import FinancialAgent


def agente(tools):
    # El llm no se usa: solo pedimos el prompt, no corremos el loop.
    return FinancialAgent(llm=None, tools=tools)


def tool_falsa(nombre="tool_nueva", argumentos="algo?", descripcion="Hace algo puntual."):
    return Tool(nombre, argumentos, descripcion, lambda **kw: [])


def test_el_prompt_nombra_todas_las_tools_registradas():
    tools = [tool_falsa("una", "a?", "La primera."), tool_falsa("otra", "b?", "La segunda.")]
    prompt = agente(tools)._build_system_prompt()
    assert "- una(a?)" in prompt and "La primera." in prompt
    assert "- otra(b?)" in prompt and "La segunda." in prompt


def test_sumar_una_tool_la_agrega_al_prompt_sin_tocar_prompt_py():
    # El corazón del ticket: el catálogo sale del registro, no de un texto a mano.
    # Si esto falla, alguien volvió a escribir la lista en prompt.py.
    base = [tool_falsa("una", "a?", "La primera.")]
    antes = agente(base)._build_system_prompt()
    despues = agente(base + [tool_falsa("recien_llegada", "x?", "Recién sumada.")])._build_system_prompt()

    assert "recien_llegada" not in antes
    assert "- recien_llegada(x?)" in despues
    assert "Recién sumada." in despues


def test_las_reglas_de_criterio_siguen_en_el_prompt():
    # Al convertir el prompt en template es fácil llevarse puesto lo que no era
    # catálogo. Estas reglas son criterio, no se derivan de ninguna tool.
    prompt = agente([tool_falsa()])._build_system_prompt()
    assert "No inventes datos" in prompt
    assert "No afirmes condiciones que no aplicaste" in prompt
    assert "fijate si hay un reporte que ya responde el pedido" in prompt
    # Y el protocolo, con las llaves bien desescapadas por el .format()
    assert '{"action": "read", "tool": "<nombre>", "args": {<argumentos>}}' in prompt
