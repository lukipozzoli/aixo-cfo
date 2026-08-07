from core.db.base import DatabaseClient


def build_database_client(provider: str, **config) -> DatabaseClient:
    # Devuelve el cliente de base de datos que corresponda según el nombre.
    # Mismo criterio que el resto de los factories: recibe la config, no la
    # busca. Así este archivo no sabe nada de ninguna empresa en particular.
    if provider == "supabase":
        from providers.db.supabase import SupabaseClient
        return SupabaseClient(**config)
    else:
        raise ValueError(f"Provider de base de datos desconocido: '{provider}'. Opciones válidas: supabase.")
