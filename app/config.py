from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # Aplicación
    app_name: str = "Intranet Empresa"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "cambiar-en-produccion"
    APP_URL: str = "http://localhost:8000"
    
    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_key: Optional[str] = None
    
    # Resend (Nueva variable agregada)
    resend_api_key: Optional[str] = None
    
    # Correo SMTP
    smtp_host: str = "smtp.hostinger.com"
    smtp_port: int = 465
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_ssl: bool = True
    email_from: str = "contacto@cytecs.mx"
    email_from_name: str = "Intranet IDS"
    
    # Empresa
    company_name: str = "Informática y Desarrollo en Sistemas S.A. de C.V."
    company_logo_url: str = "/static/img/logo.png"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Esto ignora variables extra en el .env sin lanzar error
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Obtiene la configuración cacheada"""
    return Settings()


# Instancia global de settings
settings = get_settings()
