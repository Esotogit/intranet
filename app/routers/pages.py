from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from typing import Optional

from app.auth import get_optional_user
from app.models import TokenData

router = APIRouter(tags=["Páginas"])

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def home(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Página principal - redirige según autenticación"""
    if user:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")


@router.get("/login")
async def login_page(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Página de login"""
    if user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/restablecer-password")
async def restablecer_password_page(request: Request):
    """Página para restablecer contraseña"""
    return templates.TemplateResponse("restablecer_password.html", {"request": request})


@router.get("/dashboard")
async def dashboard(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Dashboard principal"""
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user
    })


@router.get("/actividades")
async def actividades_page(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Página de captura de actividades"""
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("actividades.html", {
        "request": request,
        "user": user
    })


@router.get("/vacaciones")
async def vacaciones_page(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Página de solicitud de vacaciones"""
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("vacaciones.html", {
        "request": request,
        "user": user
    })


@router.get("/perfil")
async def perfil_page(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Página de perfil del usuario"""
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("perfil.html", {
        "request": request,
        "user": user
    })


@router.get("/mis-recibos")
async def mis_recibos_page(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Página de recibos de nómina del empleado"""
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("mis_recibos.html", {
        "request": request,
        "user": user
    })


# ===========================================
# PÁGINAS DE ADMINISTRADOR
# ===========================================

@router.get("/admin")
async def admin_home(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Dashboard de administrador"""
    if not user:
        return RedirectResponse(url="/login")
    if not user.es_admin:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user
    })


@router.get("/admin/empleados")
async def admin_empleados(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Gestión de empleados"""
    if not user or not user.es_admin:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("admin/empleados.html", {
        "request": request,
        "user": user
    })


@router.get("/admin/vacaciones")
async def admin_vacaciones(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Gestión de vacaciones"""
    if not user or not user.es_admin:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("admin/vacaciones.html", {
        "request": request,
        "user": user
    })


@router.get("/admin/reportes")
async def admin_reportes(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Generación de reportes"""
    if not user or not user.es_admin:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("admin/reportes.html", {
        "request": request,
        "user": user
    })


@router.get("/admin/catalogos")
async def admin_catalogos(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Gestión de catálogos"""
    if not user or not user.es_admin:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("admin/catalogos.html", {
        "request": request,
        "user": user
    })


@router.get("/admin/inventario")
async def admin_inventario(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Gestión de inventario de equipos"""
    # Permitir acceso a admin o usuarios con rol inventario
    if not user or (not user.es_admin and user.rol not in ['admin', 'inventario']):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("admin/inventario.html", {
        "request": request,
        "user": user
    })


@router.get("/admin/anuncios")
async def admin_anuncios(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Gestión de anuncios"""
    if not user or not user.es_admin:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("admin/anuncios.html", {
        "request": request,
        "user": user
    })


@router.get("/admin/recibos")
async def admin_recibos(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Gestión de recibos de nómina"""
    if not user or not user.es_admin:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("admin/recibos.html", {
        "request": request,
        "user": user
    })


@router.get("/admin/correos")
async def admin_correos(request: Request, user: Optional[TokenData] = Depends(get_optional_user)):
    """Gestión de plantillas de correo"""
    if not user or not user.es_admin:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("admin/correos.html", {
        "request": request,
        "user": user
    })
