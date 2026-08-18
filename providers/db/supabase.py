from supabase import create_client
from core.db.base import DatabaseClient


class SupabaseClient(DatabaseClient):
    # Implementación de DatabaseClient usando Supabase.
    # Recibe credenciales y schema desde afuera — este provider no sabe nada de AIXO.

    def __init__(self, url: str, key: str, schema: str):
        # El schema se ata una sola vez, acá: create_client(...).schema(x) devuelve
        # un cliente ya apuntado a ese espacio de tablas. Los métodos de abajo no
        # vuelven a nombrarlo, así que cambiar la forma de seleccionarlo es tocar
        # una línea y no cuatro.
        #
        # Va en el constructor y no en cada llamada porque una instancia representa
        # "el acceso a un conjunto de tablas": quien la recibe pide una tabla por
        # nombre y no tiene por qué saber en qué schema vive. Para hablarle a otro
        # schema se construye otro cliente, sin tocar la interfaz DatabaseClient.
        self._db = create_client(url, key).schema(schema)

    def select(self, table: str, filters: dict | None = None) -> list[dict]:
        query = self._db.table(table).select("*")
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        return query.execute().data

    def insert(self, table: str, data: dict) -> dict:
        result = self._db.table(table).insert(data).execute()
        return result.data[0]

    def update(self, table: str, data: dict, filters: dict) -> list[dict]:
        query = self._db.table(table).update(data)
        for column, value in filters.items():
            query = query.eq(column, value)
        return query.execute().data

    def delete(self, table: str, filters: dict) -> list[dict]:
        query = self._db.table(table).delete()
        for column, value in filters.items():
            query = query.eq(column, value)
        return query.execute().data