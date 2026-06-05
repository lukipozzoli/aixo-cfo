from core.db.base import DatabaseClient
from config.aixo import DATABASE_PROVIDER, DATABASE_URL, DATABASE_KEY

# Factory del cliente de base de datos para AIXO.
# Si en el futuro se cambia de proveedor, solo se cambia DATABASE_PROVIDER en .env.
_client: DatabaseClient | None = None


def get_client() -> DatabaseClient:
    global _client
    if _client is None:
        if DATABASE_PROVIDER == "supabase":
            from providers.db.supabase import SupabaseClient
            _client = SupabaseClient(url=DATABASE_URL, key=DATABASE_KEY)
        else:
            raise ValueError(f"Provider de base de datos desconocido: '{DATABASE_PROVIDER}'.")
    return _client
