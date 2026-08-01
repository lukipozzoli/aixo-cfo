from core.db.base import DatabaseClient

# Tools de LECTURA del dominio financiero.
# Regla del archivo: nada acá adentro escribe. Cada método llama únicamente
# db.select — nunca insert/update/delete. Esa es la garantía estructural de
# que un agente de solo lectura no puede mutar la base: no tiene en su caja
# ninguna herramienta capaz de hacerlo.


class FinancialReadTools:
    # Recibe el DatabaseClient inyectado (depende de la abstracción, no de
    # Supabase). El agente que las use NO las crea: las recibe ya armadas
    # desde main.py, atadas al schema finanzas.
    def __init__(self, db: DatabaseClient):
        self._db = db

    def buscar_cuentas(self, nombre: str | None = None) -> list[dict]:
        # Lee las cuentas con su saldo, tipo y moneda. Si se pasa un nombre,
        # filtra por coincidencia exacta (el DatabaseClient solo filtra por
        # igualdad); si no, devuelve todas. Solo consulta, nunca modifica saldos.
        if nombre:
            return self._db.select("cuenta", {"nombre": nombre})
        return self._db.select("cuenta")

    def listar_ingresos_previstos(self, estado: str | None = "pendiente") -> list[dict]:
        # Lee los ingresos previstos (plata por cobrar). Por defecto trae los
        # 'pendiente' — los cobros a recibir; pasando estado=None trae todos, o
        # un estado puntual ('confirmado', 'cancelado') si se quiere filtrar.
        # Solo lectura.
        if estado:
            return self._db.select("ingreso_previsto", {"estado": estado})
        return self._db.select("ingreso_previsto")

    def listar_egresos_previstos(self, estado: str | None = "pendiente") -> list[dict]:
        # Lee los egresos previstos (plata por pagar). Por defecto los 'pendiente'
        # (los pagos a hacer). Solo lectura.
        if estado:
            return self._db.select("egreso_previsto", {"estado": estado})
        return self._db.select("egreso_previsto")

    def listar_ingresos_efectuados(self, mes: str | None = None) -> list[dict]:
        # Lee los ingresos efectuados: la plata que realmente entró (cobros
        # concretados). 'mes' va en formato "AAAA-MM"; sin él devuelve todos.
        # Solo lectura.
        #
        # El recorte por mes se hace acá y no en la base porque DatabaseClient
        # solo filtra por igualdad exacta, y "pertenece a julio" es un rango.
        # Con el volumen actual alcanza; si crece, el filtro tiene que bajar a
        # la base, porque traer todo para descartar casi todo se vuelve caro.
        filas = self._db.select("ingreso_efectuado")
        if mes:
            filas = [f for f in filas if str(f["fecha_efectiva"]).startswith(mes)]
        return self._con_nombre_de_cuenta(filas)

    def listar_egresos_efectuados(self, mes: str | None = None) -> list[dict]:
        # Lee los egresos efectuados: la plata que realmente salió (pagos
        # concretados). 'mes' va en formato "AAAA-MM"; sin él devuelve todos.
        # Solo lectura. Mismo criterio de filtrado que listar_ingresos_efectuados.
        filas = self._db.select("egreso_efectuado")
        if mes:
            filas = [f for f in filas if str(f["fecha_efectiva"]).startswith(mes)]
        return self._con_nombre_de_cuenta(filas)

    def _con_nombre_de_cuenta(self, filas: list[dict]) -> list[dict]:
        # Cambia el id_cuenta por el nombre de la cuenta. Sin esto el agente le
        # muestra al usuario el UUID crudo, que no significa nada para nadie.
        #
        # El cruce se hace acá y no lo resuelve el agente pidiendo buscar_cuentas
        # aparte: cruzar dos listas a ojo es exactamente el tipo de trabajo que no
        # hay que delegarle a un LLM, y además costaría una vuelta más de loop.
        #
        # Si un id no aparece en el mapa se deja como estaba, para que un dato
        # inconsistente se vea en vez de desaparecer.
        cuentas = {c["id"]: c["nombre"] for c in self._db.select("cuenta")}
        return [
            {**{k: v for k, v in f.items() if k != "id_cuenta"},
             "cuenta": cuentas.get(f.get("id_cuenta"), f.get("id_cuenta"))}
            for f in filas
        ]
