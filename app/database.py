from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

# Cliente público (respeta RLS)
supabase: Client = create_client(
    settings.supabase_url,
    settings.supabase_key
)

# Cliente con permisos de servicio (bypass RLS) - usar con cuidado
def get_admin_client() -> Client:
    """Cliente con permisos de administrador para operaciones del sistema"""
    if settings.supabase_service_key:
        return create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
    return supabase
