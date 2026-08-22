from decimal import Decimal

from core.db.base import DatabaseClient
from reports.financial import FinancialReports


class BaseFalsa(DatabaseClient):
    # Base de mentira: devuelve las filas que le pasemos, sin red ni Supabase.
    # Alcanza con implementar DatabaseClient porque el reporte depende de esa
    # abstracción y no del provider concreto — el principio D de SOLID pagando.
    def __init__(self, ingresos=None, egresos=None):
        self._ingresos = ingresos or []
        self._egresos = egresos or []

    def select(self, table, filters=None):
        if table == "ingreso_efectuado":
            return self._ingresos
        if table == "egreso_efectuado":
            return self._egresos
        return []

    def insert(self, table, data): raise NotImplementedError
    def update(self, table, data, filters): raise NotImplementedError
    def delete(self, table, filters): raise NotImplementedError


def movimiento(monto, moneda="ARS", fecha="2026-07-15"):
    # Atajo para no repetir el dict completo en cada test.
    return {"monto": monto, "moneda": moneda, "fecha_efectiva": fecha}


def test_suma_muchos_montos_chicos_sin_perder_centavos():
    # El caso que motivó migrar a Decimal: con float, 1000 filas de 0.10 daban
    # 99.9999999999986 y ese número llegaba tal cual al usuario.
    db = BaseFalsa(ingresos=[movimiento(0.10)] * 1000)
    r = FinancialReports(db=db).resultado_mensual_por_moneda("2026-07")
    assert r["por_moneda"]["ARS"]["ingresos"] == Decimal("100.00")


def test_no_mezcla_monedas():
    # Sumar 100 USD con 100 ARS no da 200 de nada. Cada moneda va por su lado.
    db = BaseFalsa(
        ingresos=[movimiento(100.00, "ARS"), movimiento(50.00, "USD")],
        egresos=[movimiento(30.00, "ARS")],
    )
    r = FinancialReports(db=db).resultado_mensual_por_moneda("2026-07")
    assert r["por_moneda"]["ARS"]["resultado"] == Decimal("70.00")
    assert r["por_moneda"]["USD"]["resultado"] == Decimal("50.00")


def test_filtra_por_mes():
    # El movimiento de junio no tiene que entrar en el resultado de julio.
    db = BaseFalsa(ingresos=[
        movimiento(100.00, fecha="2026-07-05"),
        movimiento(999.00, fecha="2026-06-30"),
    ])
    r = FinancialReports(db=db).resultado_mensual_por_moneda("2026-07")
    assert r["por_moneda"]["ARS"]["ingresos"] == Decimal("100.00")


def test_mes_sin_movimientos_devuelve_vacio():
    db = BaseFalsa(ingresos=[movimiento(100.00, fecha="2026-07-05")])
    r = FinancialReports(db=db).resultado_mensual_por_moneda("2026-01")
    assert r["por_moneda"] == {}


def test_mes_con_perdida_da_resultado_negativo():
    # Una moneda que solo tuvo egresos: ingresos en 0.00 y resultado negativo.
    db = BaseFalsa(egresos=[movimiento(120.55, "EUR")])
    r = FinancialReports(db=db).resultado_mensual_por_moneda("2026-07")
    assert r["por_moneda"]["EUR"]["ingresos"] == Decimal("0.00")
    assert r["por_moneda"]["EUR"]["resultado"] == Decimal("-120.55")


def test_siempre_dos_decimales():
    # Sin quantize, 0.10 tres veces da Decimal('0.3') y se muestra "$0.3".
    db = BaseFalsa(ingresos=[movimiento(0.10)] * 3)
    r = FinancialReports(db=db).resultado_mensual_por_moneda("2026-07")
    assert str(r["por_moneda"]["ARS"]["ingresos"]) == "0.30"