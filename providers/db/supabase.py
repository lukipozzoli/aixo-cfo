from supabase import create_client, Client
from core.db.base import DatabaseClient


class SupabaseClient(DatabaseClient):
    # Implementación de DatabaseClient usando Supabase.
    # Recibe las credenciales desde afuera — este provider no sabe nada de AIXO.

    def __init__(self, url: str, key: str):
        self._client: Client = create_client(url, key)

    def select(self, table: str, filters: dict | None = None) -> list[dict]:
        query = self._client.schema("finanzas").table(table).select("*")
        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)
        return query.execute().data

    def insert(self, table: str, data: dict) -> dict:
        result = self._client.schema("finanzas").table(table).insert(data).execute()
        return result.data[0]

    def update(self, table: str, data: dict, filters: dict) -> list[dict]:
        query = self._client.schema("finanzas").table(table).update(data)
        for column, value in filters.items():
            query = query.eq(column, value)
        return query.execute().data

    def delete(self, table: str, filters: dict) -> list[dict]:
        query = self._client.schema("finanzas").table(table).delete()
        for column, value in filters.items():
            query = query.eq(column, value)
        return query.execute().data
