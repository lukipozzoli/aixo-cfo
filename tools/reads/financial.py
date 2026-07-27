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