from datetime import date
from decimal import Decimal
from core.tools.base import Tool

from core.db.base import DatabaseClient

# Reportes financieros: cálculo determinista sobre los datos de la base.
#
# Regla del archivo: la aritmética con dinero la hace SIEMPRE el código, nunca
# el LLM. Un LLM predice texto, no calcula — pedirle que sume plata es pedirle
# que adivine. El LLM elige QUÉ reporte pedir; los números los pone el código.
#
# Convención de tipos: usa Decimal TODO número que participe en una cuenta con
# dinero — montos, porcentajes de reparto y tipos de cambio. Lo que no entra en
# una cuenta (fechas, ids, estados, conteos) no lo necesita.
#
# El motivo: la librería de la base devuelve los numeric como float, y encadenar
# operaciones con floats acumula error. Decimal es aritmética decimal exacta,
# igual que la columna numeric(15,2) de la que salen los datos.
#
# La regla se enforcea sola: Python no permite Decimal * float. Si un porcentaje
# o un tipo de cambio quedaran como float, la operación explota en vez de
# devolver un número silenciosamente mal.

# Escala de los montos: 2 decimales, la misma que numeric(15,2) en la base.
# Vive acá y no suelto en el código para que cambiarla sea un solo lugar.
ESCALA_MONTO = Decimal("0.01")

# Formato del período que recibe el reporte y con el que se comparan las fechas.
FORMATO_MES = "%Y-%m"


class FinancialReports:
    # Recibe el DatabaseClient inyectado: depende de la abstracción, no de
    # Supabase (principio D de SOLID). Esto además permite probar el reporte
    # con una base falsa, sin red.
    #
    # No consume las tools de lectura a propósito: un reporte es un par de las
    # tools, no un consumidor. Ambos dependen del mismo DatabaseClient, así que
    # ninguno arrastra los cambios del otro.
    #
    # Vive fuera de los agentes (igual que tools/) para que cualquier sub-agente
    # pueda recibir esta misma instancia inyectada desde main.py.
    def __init__(self, db: DatabaseClient):
        self._db = db

    def resultado_mensual_por_moneda(self, mes: str | None = None) -> dict:
        # Resultado del mes: lo que entró menos lo que salió, separado por moneda.
        # Se calcula sobre lo EFECTUADO y no sobre lo previsto porque el resultado
        # es plata que existe, no promesas de cobro.
        #
        # 'mes' llega como "AAAA-MM". Si no viene, se asume el mes actual.
        if not mes:
            mes = date.today().strftime(FORMATO_MES)

        ingresos = self._filtrar_por_mes(self._db.select("ingreso_efectuado"), mes)
        egresos = self._filtrar_por_mes(self._db.select("egreso_efectuado"), mes)

        # Se agrupa por las monedas realmente presentes en los datos y no por una
        # lista fija: si mañana entra una moneda nueva a la base, el reporte la
        # incluye sin tocar este archivo (principio O de SOLID).
        monedas = {r["moneda"] for r in ingresos} | {r["moneda"] for r in egresos}

        # sorted() para que el orden de salida sea estable entre corridas: un
        # reporte que cambia de orden solo es imposible de comparar o testear.
        resultado: dict = {"mes": mes, "por_moneda": {}}
        for moneda in sorted(monedas):
            total_ingresos = self._sumar(ingresos, moneda)
            total_egresos = self._sumar(egresos, moneda)
            resultado["por_moneda"][moneda] = {
                "ingresos": total_ingresos,
                "egresos": total_egresos,
                # El neto se calcula dentro del grupo de cada moneda: sumar
                # 100 USD con 100 ARS no da 200 de nada. Convertir entre monedas
                # exige un tipo de cambio, que es una decisión aparte.
                "resultado": total_ingresos - total_egresos,
            }
        return resultado

    def _filtrar_por_mes(self, filas: list[dict], mes: str) -> list[dict]:
        # El recorte por mes se hace en Python porque DatabaseClient solo filtra
        # por igualdad exacta, y "pertenece a julio" es un rango. Con el volumen
        # actual alcanza; si crece, este filtro tiene que bajar a la base, porque
        # traer todo para descartar casi todo se vuelve caro.
        #
        # Las fechas llegan como "AAAA-MM-DD", así que comparar el prefijo evita
        # parsear. str() por si el driver devolviera un date en vez de texto.
        return [f for f in filas if str(f["fecha_efectiva"]).startswith(mes)]

    def _sumar(self, filas: list[dict], moneda: str) -> Decimal:
        # Decimal(str(...)) y no Decimal(...): construir un Decimal desde un float
        # hereda el error binario del float — Decimal(1000.10) da
        # 1000.1000000000000227... Pasando por str se recupera el valor exacto.
        total = sum(
            (Decimal(str(f["monto"])) for f in filas if f["moneda"] == moneda),
            # Valor inicial explícito: sin él, un grupo vacío devolvería un int 0
            # y el tipo del resultado dependería de los datos, que es de las cosas
            # más molestas de debuggear.
            Decimal("0.00"),
        )
        # quantize fija la escala en 2 decimales para que 3000.3 se muestre como
        # 3000.30. Acá no redondea nada: una suma de valores de 2 decimales ya
        # tiene 2 decimales. Solo empareja la escala.
        return total.quantize(ESCALA_MONTO)

    def catalogo(self) -> list[Tool]:
        # Un reporte se describe igual que una tool: para el LLM los dos son "algo
        # que puedo pedir". La diferencia —datos crudos contra números calculados—
        # importa acá adentro, no del lado del agente.
        return [
            Tool(
                "resultado_mensual_por_moneda", "mes?",
                "Calcula el resultado de un mes: ingresos efectuados menos egresos efectuados, "
                "separado por moneda. 'mes' es opcional, formato \"AAAA-MM\" (ej: \"2026-07\"); "
                "sin argumento usa el mes actual. Los números vienen calculados por código: "
                "usalos tal cual, no rehagas las cuentas.",
                self.resultado_mensual_por_moneda,
            ),
        ]