from core.db.base import DatabaseClient
from core.tools.base import Tool
from tools.reads.financial import FinancialReadTools
from reports.financial import FinancialReports


class BaseFalsa(DatabaseClient):
    # Base de mentira: alcanza con cumplir DatabaseClient porque las tools
    # dependen de esa abstracción y no del provider concreto.
    def select(self, table, filters=None):
        if table != "cuenta":
            return []
        filas = [{"id": "a1", "nombre": "Galicia", "tipo": "bancaria",
                  "moneda": "ARS", "saldo_actual": 100.00}]
        # Igualdad exacta, igual que el .eq() de Postgres en SupabaseClient.
        if filters:
            filas = [f for f in filas if all(f.get(k) == v for k, v in filters.items())]
        return filas

    def insert(self, table, data): raise NotImplementedError
    def update(self, table, data, filters): raise NotImplementedError
    def delete(self, table, filters): raise NotImplementedError


def catalogo_completo():
    db = BaseFalsa()
    return FinancialReadTools(db=db).catalogo() + FinancialReports(db=db).catalogo()


def test_el_catalogo_expone_las_seis_con_nombres_unicos():
    catalogo = catalogo_completo()
    nombres = [t.nombre for t in catalogo]
    # Nombres repetidos se pisarían al armar la whitelist del agente y una de las
    # dos tools quedaría inalcanzable, sin que nada falle.
    assert len(nombres) == len(set(nombres)) == 6


def test_toda_tool_esta_completa_y_es_ejecutable():
    for tool in catalogo_completo():
        assert isinstance(tool, Tool)
        assert tool.nombre and tool.argumentos is not None and tool.descripcion
        assert callable(tool.ejecutar)


def test_ejecutar_corre_el_metodo_real():
    # La Tool no es una etiqueta suelta: ejecutar tiene que llamar al método de
    # verdad, ya atado a su instancia y a su base de datos.
    buscar = next(t for t in catalogo_completo() if t.nombre == "buscar_cuentas")
    assert buscar.ejecutar() == [{"id": "a1", "nombre": "Galicia", "tipo": "bancaria",
                                  "moneda": "ARS", "saldo_actual": 100.00}]
    assert buscar.ejecutar(nombre="No existe") == []
