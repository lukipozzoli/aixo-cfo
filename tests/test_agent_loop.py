import asyncio

from core.agents.loop import AgentLoop, LoopMessages

MENSAJES = LoopMessages(
    parseo_fallido="no pude interpretar",
    iteraciones_agotadas="demasiados pasos",
    formato_invalido="formato invalido",
)


class LLMFalso:
    # Devuelve las respuestas de un guion y guarda una copia congelada de lo que
    # recibió en cada llamada, para poder mirar cómo creció el historial.
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.recibido = []

    async def chat(self, messages, **kwargs):
        self.recibido.append([dict(m) for m in messages])
        return self.respuestas.pop(0) if self.respuestas else '{"action": "otra"}'

    async def complete(self, prompt, **kwargs):
        raise NotImplementedError


def correr(llm, acciones=None, max_iterations=5):
    loop = AgentLoop(
        llm=llm,
        nombre="test",
        acciones=acciones or {},
        mensajes=MENSAJES,
        max_iterations=max_iterations,
    )
    return asyncio.run(loop.run([{"role": "system", "content": "prompt"}]))


def test_respond_corta_el_loop_y_devuelve_el_texto():
    llm = LLMFalso('{"action": "respond", "text": "listo"}')
    resultado = correr(llm)
    assert resultado.text == "listo"
    assert resultado.success is True
    # Una sola llamada: apenas ve un "respond" no vuelve a preguntar.
    assert len(llm.recibido) == 1


def test_una_accion_del_catalogo_realimenta_el_historial():
    async def leer(decision):
        return "[Resultado]: 3 filas"

    llm = LLMFalso(
        '{"action": "leer"}',
        '{"action": "respond", "text": "son 3"}',
    )
    resultado = correr(llm, acciones={"leer": leer})
    assert resultado.text == "son 3"
    # La segunda llamada tiene que ver el resultado de la primera, si no el LLM
    # decidiría a ciegas y volvería a pedir lo mismo.
    assert "[Resultado]: 3 filas" in llm.recibido[1][-1]["content"]


def test_accion_desconocida_le_avisa_al_llm_en_vez_de_repetir():
    # El bug que tenía el orquestador: sin rama para la acción desconocida, el
    # historial no crecía y el LLM recibía el MISMO prompt las 5 vueltas, sin
    # forma de enterarse de que se había equivocado.
    llm = LLMFalso('{"action": "pensar"}', '{"action": "pensar"}')
    correr(llm, max_iterations=2)

    assert len(llm.recibido) == 2
    assert llm.recibido[0] != llm.recibido[1]
    assert llm.recibido[1][-1]["content"] == "formato invalido"


def test_json_valido_que_no_es_un_objeto_no_revienta():
    # json.loads('["read"]') no falla: devuelve una lista, y el .get() de después
    # tiraba AttributeError. Tiene que tratarse como una decisión no parseable.
    for respuesta in ('["read", "buscar_cuentas"]', '"respond"', "42"):
        resultado = correr(LLMFalso(respuesta))
        assert resultado.text == "no pude interpretar"
        assert resultado.success is False


def test_se_agotan_las_iteraciones_sin_colgarse():
    async def leer(decision):
        return "mas datos"

    llm = LLMFalso('{"action": "leer"}', '{"action": "leer"}', '{"action": "leer"}')
    resultado = correr(llm, acciones={"leer": leer}, max_iterations=3)
    assert resultado.text == "demasiados pasos"
    assert resultado.success is False
    assert len(llm.recibido) == 3
