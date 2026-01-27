from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.database import supabase, get_admin_client
from app.models import (
    Puesto, PuestoBase,
    Supervisor, SupervisorBase,
    Ubicacion, UbicacionBase,
    Proyecto, ProyectoBase,
    TokenData
)
from app.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/api/catalogos", tags=["Catálogos"])


# ===========================================
# PUESTOS
# ===========================================

@router.get("/puestos", response_model=List[Puesto])
async def listar_puestos(current_user: TokenData = Depends(get_current_user)):
    """Listar todos los puestos activos"""
    result = supabase.table("puestos").select("*").eq("activo", True).order("nombre").execute()
    return result.data


@router.post("/puestos", response_model=Puesto, status_code=status.HTTP_201_CREATED)
async def crear_puesto(
    puesto: PuestoBase,
    current_user: TokenData = Depends(get_current_admin)
):
    """Crear un nuevo puesto (solo admin)"""
    result = supabase.table("puestos").insert(puesto.model_dump()).execute()
    return result.data[0]


@router.patch("/puestos/{puesto_id}", response_model=Puesto)
async def actualizar_puesto(
    puesto_id: int,
    puesto: PuestoBase,
    current_user: TokenData = Depends(get_current_admin)
):
    """Actualizar un puesto (solo admin)"""
    result = supabase.table("puestos").update(puesto.model_dump()).eq("id", puesto_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Puesto no encontrado")
    return result.data[0]


@router.delete("/puestos/{puesto_id}")
async def eliminar_puesto(
    puesto_id: int,
    current_user: TokenData = Depends(get_current_admin)
):
    """Desactivar un puesto (solo admin)"""
    result = supabase.table("puestos").update({"activo": False}).eq("id", puesto_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Puesto no encontrado")
    return {"message": "Puesto desactivado"}


# ===========================================
# SUPERVISORES
# ===========================================

@router.get("/supervisores", response_model=List[Supervisor])
async def listar_supervisores(current_user: TokenData = Depends(get_current_user)):
    """Listar todos los supervisores activos"""
    result = supabase.table("supervisores").select("*").eq("activo", True).order("nombre").execute()
    return result.data


@router.post("/supervisores", response_model=Supervisor, status_code=status.HTTP_201_CREATED)
async def crear_supervisor(
    supervisor: SupervisorBase,
    current_user: TokenData = Depends(get_current_admin)
):
    """Crear un nuevo supervisor (solo admin)"""
    result = supabase.table("supervisores").insert(supervisor.model_dump()).execute()
    return result.data[0]


@router.patch("/supervisores/{supervisor_id}", response_model=Supervisor)
async def actualizar_supervisor(
    supervisor_id: int,
    supervisor: SupervisorBase,
    current_user: TokenData = Depends(get_current_admin)
):
    """Actualizar un supervisor (solo admin)"""
    result = supabase.table("supervisores").update(supervisor.model_dump()).eq("id", supervisor_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Supervisor no encontrado")
    return result.data[0]


@router.delete("/supervisores/{supervisor_id}")
async def eliminar_supervisor(
    supervisor_id: int,
    current_user: TokenData = Depends(get_current_admin)
):
    """Desactivar un supervisor (solo admin)"""
    result = supabase.table("supervisores").update({"activo": False}).eq("id", supervisor_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Supervisor no encontrado")
    return {"message": "Supervisor desactivado"}


# ===========================================
# UBICACIONES
# ===========================================

@router.get("/ubicaciones", response_model=List[Ubicacion])
async def listar_ubicaciones(current_user: TokenData = Depends(get_current_user)):
    """Listar todas las ubicaciones activas"""
    result = supabase.table("ubicaciones").select("*").eq("activo", True).order("nombre").execute()
    return result.data


@router.post("/ubicaciones", response_model=Ubicacion, status_code=status.HTTP_201_CREATED)
async def crear_ubicacion(
    ubicacion: UbicacionBase,
    current_user: TokenData = Depends(get_current_admin)
):
    """Crear una nueva ubicación (solo admin)"""
    result = supabase.table("ubicaciones").insert(ubicacion.model_dump()).execute()
    return result.data[0]


@router.patch("/ubicaciones/{ubicacion_id}", response_model=Ubicacion)
async def actualizar_ubicacion(
    ubicacion_id: int,
    ubicacion: UbicacionBase,
    current_user: TokenData = Depends(get_current_admin)
):
    """Actualizar una ubicación (solo admin)"""
    result = supabase.table("ubicaciones").update(ubicacion.model_dump()).eq("id", ubicacion_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    return result.data[0]


@router.delete("/ubicaciones/{ubicacion_id}")
async def eliminar_ubicacion(
    ubicacion_id: int,
    current_user: TokenData = Depends(get_current_admin)
):
    """Desactivar una ubicación (solo admin)"""
    result = supabase.table("ubicaciones").update({"activo": False}).eq("id", ubicacion_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Ubicación no encontrada")
    return {"message": "Ubicación desactivada"}


# ===========================================
# PROYECTOS
# ===========================================

@router.get("/proyectos", response_model=List[Proyecto])
async def listar_proyectos(current_user: TokenData = Depends(get_current_user)):
    """Listar todos los proyectos activos"""
    result = supabase.table("proyectos").select("*").eq("activo", True).order("nombre").execute()
    return result.data


@router.post("/proyectos", response_model=Proyecto, status_code=status.HTTP_201_CREATED)
async def crear_proyecto(
    proyecto: ProyectoBase,
    current_user: TokenData = Depends(get_current_admin)
):
    """Crear un nuevo proyecto (solo admin)"""
    result = supabase.table("proyectos").insert(proyecto.model_dump()).execute()
    return result.data[0]


@router.patch("/proyectos/{proyecto_id}", response_model=Proyecto)
async def actualizar_proyecto(
    proyecto_id: int,
    proyecto: ProyectoBase,
    current_user: TokenData = Depends(get_current_admin)
):
    """Actualizar un proyecto (solo admin)"""
    result = supabase.table("proyectos").update(proyecto.model_dump()).eq("id", proyecto_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return result.data[0]


@router.delete("/proyectos/{proyecto_id}")
async def eliminar_proyecto(
    proyecto_id: int,
    current_user: TokenData = Depends(get_current_admin)
):
    """Desactivar un proyecto (solo admin)"""
    result = supabase.table("proyectos").update({"activo": False}).eq("id", proyecto_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {"message": "Proyecto desactivado"}


# ===========================================
# MARCAS (Inventario)
# ===========================================

@router.get("/marcas")
async def listar_marcas(current_user: TokenData = Depends(get_current_user)):
    """Listar todas las marcas activas"""
    admin_client = get_admin_client()
    result = admin_client.table("marcas").select("*").eq("activo", True).order("nombre").execute()
    return result.data


@router.post("/marcas", status_code=status.HTTP_201_CREATED)
async def crear_marca(
    marca: dict,
    current_user: TokenData = Depends(get_current_admin)
):
    """Crear una nueva marca (solo admin)"""
    admin_client = get_admin_client()
    result = admin_client.table("marcas").insert({"nombre": marca.get("nombre")}).execute()
    return result.data[0]


@router.patch("/marcas/{marca_id}")
async def actualizar_marca(
    marca_id: str,
    marca: dict,
    current_user: TokenData = Depends(get_current_admin)
):
    """Actualizar una marca (solo admin)"""
    admin_client = get_admin_client()
    result = admin_client.table("marcas").update({"nombre": marca.get("nombre")}).eq("id", marca_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    return result.data[0]


@router.delete("/marcas/{marca_id}")
async def eliminar_marca(
    marca_id: str,
    current_user: TokenData = Depends(get_current_admin)
):
    """Desactivar una marca (solo admin)"""
    admin_client = get_admin_client()
    result = admin_client.table("marcas").update({"activo": False}).eq("id", marca_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    return {"message": "Marca desactivada"}
