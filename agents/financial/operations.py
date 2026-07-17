from datetime import date

from core.db.base import DatabaseClient

# Operaciones financieras validadas. Cada función valida sus datos ANTES de
# tocar la base — el LLM del agente decide qué operación llamar y con qué
# argumentos, pero nunca escribe en la base sin pasar por estas validaciones.

MONEDAS_VALIDAS = ("ARS", "USD", "EUR")
TIPOS_CUENTA_VALIDOS = ("bancaria", "billetera_virtual", "efectivo")


class OperationError(Exception):
    # Error de validación u operación. El mensaje está pensado para que el
    # agente se lo pueda explicar al usuario en lenguaje natural.
    pass


class FinancialOperations:
    # Recibe el cliente de base de datos inyectado — depende de la abstracción,
    # no de Supabase (principio D). Esto además permite testear con una DB falsa.

    def __init__(self, db: DatabaseClient):
        self._db = db

    # ---------- Cuentas ----------

    def crear_cuenta(self, nombre: str, tipo: str, moneda: str) -> dict:
        if not nombre or not nombre.strip():
            raise OperationError("El nombre de la cuenta no puede estar vacío.")
        if tipo not in TIPOS_CUENTA_VALIDOS:
            raise OperationError(f"Tipo de cuenta inválido: '{tipo}'. Válidos: {TIPOS_CUENTA_VALIDOS}.")
        if moneda not in MONEDAS_VALIDAS:
            raise OperationError(f"Moneda inválida: '{moneda}'. Válidas: {MONEDAS_VALIDAS}.")

        # Evita duplicados por nombre — dos cuentas "Galicia" serían inmanejables
        # para el agente al momento de resolver a cuál registrar un movimiento.
        existentes = self._db.select("cuenta", {"nombre": nombre.strip()})
        if existentes:
            raise OperationError(f"Ya existe una cuenta llamada '{nombre}'.")

        return self._db.insert("cuenta", {
            "nombre": nombre.strip(),
            "tipo": tipo,
            "moneda": moneda,
        })

    def listar_cuentas(self) -> list[dict]:
        return self._db.select("cuenta")

    # ---------- Egresos ----------

    def registrar_egreso(
        self,
        monto: float,
        moneda: str,
        cuenta_nombre: str,
        descripcion: str | None = None,
        fecha: str | None = None,  # formato ISO "2026-07-16"; si falta, hoy
    ) -> dict:
        cuenta = self._buscar_cuenta(cuenta_nombre)
        self._validar_monto_y_moneda(monto, moneda, cuenta)

        egreso = self._db.insert("egreso_efectuado", {
            "monto": monto,
            "moneda": moneda,
            "id_cuenta": cuenta["id"],
            "descripcion": descripcion,
            "fecha_efectiva": fecha or date.today().isoformat(),
        })

        # Regla de negocio del diseño: cada movimiento actualiza el saldo.
        nuevo_saldo = float(cuenta["saldo_actual"]) - monto
        self._db.update("cuenta", {"saldo_actual": nuevo_saldo}, {"id": cuenta["id"]})

        return egreso

    # ---------- Ingresos previstos ----------

    def registrar_ingreso_previsto(
        self,
        monto: float,
        moneda: str,
        fecha_esperada: str,  # obligatoria: sin fecha no hay previsión
        descripcion: str | None = None,
    ) -> dict:
        if monto <= 0:
            raise OperationError("El monto debe ser mayor a cero.")
        if moneda not in MONEDAS_VALIDAS:
            raise OperationError(f"Moneda inválida: '{moneda}'. Válidas: {MONEDAS_VALIDAS}.")
        if not fecha_esperada:
            raise OperationError("Falta la fecha esperada de cobro.")

        return self._db.insert("ingreso_previsto", {
            "monto": monto,
            "moneda": moneda,
            "fecha_esperada": fecha_esperada,
            "descripcion": descripcion,
            # estado no se manda: la base le pone 'pendiente' por default
        })

    def listar_ingresos_previstos(self) -> list[dict]:
        return self._db.select("ingreso_previsto", {"estado": "pendiente"})
    
    # ---------- Ingresos efectuados ----------

    def registrar_ingreso_efectuado(
        self,
        monto: float,
        moneda: str,
        cuenta_nombre: str,
        descripcion: str | None = None,
        fecha: str | None = None,
        id_ingreso_previsto: str | None = None,  # si viene, concilia el previsto
    ) -> dict:
        cuenta = self._buscar_cuenta(cuenta_nombre)
        self._validar_monto_y_moneda(monto, moneda, cuenta)

        # Conciliación: si el cobro corresponde a un ingreso previsto,
        # ese previsto pasa a 'confirmado' — deja de estar pendiente de cobro.
        if id_ingreso_previsto:
            previstos = self._db.select("ingreso_previsto", {"id": id_ingreso_previsto})
            if not previstos:
                raise OperationError(f"No existe un ingreso previsto con id '{id_ingreso_previsto}'.")
            self._db.update("ingreso_previsto", {"estado": "confirmado"}, {"id": id_ingreso_previsto})

        ingreso = self._db.insert("ingreso_efectuado", {
            "monto": monto,
            "moneda": moneda,
            "id_cuenta": cuenta["id"],
            "descripcion": descripcion,
            "fecha_efectiva": fecha or date.today().isoformat(),
            "id_ingreso_previsto": id_ingreso_previsto,
        })

        # La plata entró: el saldo de la cuenta sube.
        nuevo_saldo = float(cuenta["saldo_actual"]) + monto
        self._db.update("cuenta", {"saldo_actual": nuevo_saldo}, {"id": cuenta["id"]})

        return ingreso

    # ---------- Resumen ----------

    def resumen_mensual(self, mes: str | None = None) -> dict:
        # mes en formato "AAAA-MM"; si falta, el mes actual.
        # Calcula sobre lo EFECTUADO (cobrado y pagado), no sobre lo previsto:
        # la ganancia es plata que existe, no promesas.
        if not mes:
            mes = date.today().strftime("%Y-%m")

        # El DatabaseClient solo filtra por igualdad exacta, así que el filtro
        # por mes se hace acá. Con pocos registros alcanza; a optimizar a futuro.
        ingresos = [r for r in self._db.select("ingreso_efectuado")
                    if str(r["fecha_efectiva"]).startswith(mes)]
        egresos = [r for r in self._db.select("egreso_efectuado")
                   if str(r["fecha_efectiva"]).startswith(mes)]

        # Totales separados por moneda — nunca se suman peras con manzanas.
        resumen: dict = {"mes": mes, "por_moneda": {}}
        for moneda in MONEDAS_VALIDAS:
            total_ing = sum(float(r["monto"]) for r in ingresos if r["moneda"] == moneda)
            total_egr = sum(float(r["monto"]) for r in egresos if r["moneda"] == moneda)
            if total_ing == 0 and total_egr == 0:
                continue
            neto = total_ing - total_egr
            resumen["por_moneda"][moneda] = {
                "ingresos": total_ing,
                "egresos": total_egr,
                "ganancia_neta": neto,
                "mitad_por_socio": neto / 2,
            }
        return resumen

    # ---------- Helpers internos ----------

    def _buscar_cuenta(self, nombre: str) -> dict:
        # Búsqueda por nombre exacto. El prompt del agente le pide resolver el
        # nombre real con listar_cuentas si el usuario usa un apodo.
        cuentas = self._db.select("cuenta", {"nombre": nombre})
        if not cuentas:
            raise OperationError(
                f"No existe una cuenta llamada '{nombre}'. Usá listar_cuentas para ver las disponibles."
            )
        return cuentas[0]

    def _validar_monto_y_moneda(self, monto: float, moneda: str, cuenta: dict) -> None:
        if monto <= 0:
            raise OperationError("El monto debe ser mayor a cero.")
        if moneda not in MONEDAS_VALIDAS:
            raise OperationError(f"Moneda inválida: '{moneda}'. Válidas: {MONEDAS_VALIDAS}.")
        if moneda != cuenta["moneda"]:
            raise OperationError(
                f"La cuenta '{cuenta['nombre']}' es en {cuenta['moneda']}, no en {moneda}."
            )