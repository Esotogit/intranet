from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

from app.config import get_settings
from app.scheduler import iniciar_scheduler, detener_scheduler

# Importar routers
from app.routers import auth, empleados, vacaciones, actividades, catalogos, reportes, pages, inventario, anuncios, recibos, correos

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja el ciclo de vida de la aplicación"""
    # Startup
    print(f"🚀 Iniciando {settings.app_name}...")
    iniciar_scheduler()
    yield
    # Shutdown
    print("👋 Cerrando aplicación...")
    detener_scheduler()


# Crear aplicación
app = FastAPI(
    title=settings.app_name,
    description="Sistema de gestión de empleados, vacaciones y actividades",
    version="1.0.0",
    lifespan=lifespan
)


# Handler para errores de validación (422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Muestra detalles de errores de validación en consola"""
    print(f"[VALIDATION ERROR] URL: {request.url}")
    print(f"[VALIDATION ERROR] Body: {await request.body()}")
    print(f"[VALIDATION ERROR] Errors: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Registrar routers de API
app.include_router(auth.router)
app.include_router(empleados.router)
app.include_router(vacaciones.router)
app.include_router(actividades.router)
app.include_router(catalogos.router)
app.include_router(reportes.router)
app.include_router(inventario.router)
app.include_router(anuncios.router)
app.include_router(recibos.router)
app.include_router(correos.router)

# Registrar router de páginas HTML
app.include_router(pages.router)


@app.get("/health")
async def health_check():
    """Endpoint de salud para verificar que la API está funcionando"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "environment": settings.app_env
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
