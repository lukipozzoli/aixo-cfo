from abc import ABC, abstractmethod


class DatabaseClient(ABC):
    # Interfaz genérica para cualquier proveedor de base de datos.
    # Los agentes dependen de esta abstracción, nunca de Supabase directamente.

    @abstractmethod
    def select(self, table: str, filters: dict | None = None) -> list[dict]:
        # Devuelve filas de una tabla. filters es un dict de columna → valor exacto.
        pass

    @abstractmethod
    def insert(self, table: str, data: dict) -> dict:
        # Inserta una fila y devuelve el registro creado.
        pass

    @abstractmethod
    def update(self, table: str, data: dict, filters: dict) -> list[dict]:
        # Actualiza filas que cumplan filters y devuelve los registros modificados.
        pass

    @abstractmethod
    def delete(self, table: str, filters: dict) -> list[dict]:
        # Elimina filas que cumplan filters y devuelve los registros eliminados.
        pass
