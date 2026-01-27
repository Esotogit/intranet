from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List, Optional
from io import BytesIO

from app.database import supabase
from app.models import (
    Vacaciones,
    VacacionesCreate,
    VacacionesUpdate,
    EstatusVacaciones,
    TokenData
)
from app.auth import get_current_user, get_current_admin
from app.services.pdf_generator import generar_formato_vacaciones

router = APIRouter(prefix="/api/vacaciones", tags=["Vacaciones"])


@router.get("/mis-solicitudes", response_model=List[Vacaciones])
async def mis_solicitudes(
    estatus: Optional[EstatusVacaciones] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Obtener mis solicitudes de vacaciones"""
    
    query = supabase.table("vacaciones").select("*").eq("empleado_id", current_user.user_id)
    
    if estatus:
        query = query.eq("estatus", estatus.value)
    
    result = query.order("created_at", desc=True).execute()
    
    return result.data


@router.post("/", response_model=Vacaciones, status_code=status.HTTP_201_CREATED)
async def solicitar_vacaciones(
    vacaciones: VacacionesCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Crear una solicitud de vacaciones"""
    
    # Verificar que el empleado tenga días disponibles
    empleado_result = supabase.table("empleados").select("dias_vacaciones").eq("id", current_user.user_id).execute()
    
    if not empleado_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    
    dias_disponibles = float(empleado_result.data[0]["dias_vacaciones"])
    
    if float(vacaciones.dias_solicitados) > dias_disponibles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No tienes suficientes días disponibles. Tienes {dias_disponibles} días."
        )
    
    # Verificar que no haya traslape con otras vacaciones aprobadas
    traslape = supabase.table("vacaciones").select("id").eq("empleado_id", current_user.user_id).eq("estatus", "aprobada").gte("fecha_fin", vacaciones.fecha_inicio.isoformat()).lte("fecha_inicio", vacaciones.fecha_fin.isoformat()).execute()
    
    if traslape.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya tienes vacaciones aprobadas en esas fechas"
        )
    
    # Crear la solicitud
    vacaciones_data = vacaciones.model_dump()
    vacaciones_data["empleado_id"] = current_user.user_id
    vacaciones_data["fecha_inicio"] = vacaciones.fecha_inicio.isoformat()
    vacaciones_data["fecha_fin"] = vacaciones.fecha_fin.isoformat()
    vacaciones_data["dias_solicitados"] = str(vacaciones.dias_solicitados)
    
    result = supabase.table("vacaciones").insert(vacaciones_data).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear solicitud"
        )
    
    return result.data[0]


@router.get("/pendientes", response_model=List[dict])
async def listar_pendientes(
    current_user: TokenData = Depends(get_current_admin)
):
    """Listar solicitudes pendientes (solo admin)"""
    
    result = supabase.table("v_vacaciones_pendientes").select("*").execute()
    
    return result.data


@router.get("/todas", response_model=List[dict])
async def listar_todas(
    estatus: Optional[EstatusVacaciones] = None,
    current_user: TokenData = Depends(get_current_admin)
):
    """Listar todas las solicitudes (solo admin)"""
    
    # Especificar la relación explícita para evitar ambigüedad
    query = supabase.table("vacaciones").select(
        "*, empleado:empleados!vacaciones_empleado_id_fkey(nombre, apellidos)"
    )
    
    if estatus:
        query = query.eq("estatus", estatus.value)
    
    result = query.order("created_at", desc=True).execute()
    
    return result.data


@router.patch("/{vacacion_id}/aprobar", response_model=Vacaciones)
async def aprobar_vacaciones(
    vacacion_id: str,
    comentario: Optional[str] = None,
    current_user: TokenData = Depends(get_current_admin)
):
    """Aprobar una solicitud de vacaciones (solo admin)"""
    
    update_data = {
        "estatus": EstatusVacaciones.APROBADA.value,
        "aprobado_por": current_user.user_id
    }
    
    if comentario:
        update_data["comentario_admin"] = comentario
    
    result = supabase.table("vacaciones").update(update_data).eq("id", vacacion_id).eq("estatus", "pendiente").execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada o ya fue procesada"
        )
    
    return result.data[0]


@router.patch("/{vacacion_id}/rechazar", response_model=Vacaciones)
async def rechazar_vacaciones(
    vacacion_id: str,
    comentario: str,
    current_user: TokenData = Depends(get_current_admin)
):
    """Rechazar una solicitud de vacaciones (solo admin)"""
    
    result = supabase.table("vacaciones").update({
        "estatus": EstatusVacaciones.RECHAZADA.value,
        "aprobado_por": current_user.user_id,
        "comentario_admin": comentario
    }).eq("id", vacacion_id).eq("estatus", "pendiente").execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada o ya fue procesada"
        )
    
    return result.data[0]


@router.delete("/{vacacion_id}")
async def cancelar_solicitud(
    vacacion_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Cancelar mi solicitud de vacaciones (solo si está pendiente)"""
    
    result = supabase.table("vacaciones").delete().eq("id", vacacion_id).eq("empleado_id", current_user.user_id).eq("estatus", "pendiente").execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada o no se puede cancelar"
        )
    
    return {"message": "Solicitud cancelada correctamente"}


@router.get("/{vacacion_id}/pdf")
async def descargar_pdf_vacaciones(
    vacacion_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Descargar el formato PDF de una solicitud de vacaciones"""
    
    # Obtener la solicitud
    vacacion_result = supabase.table("vacaciones").select("*").eq("id", vacacion_id).execute()
    
    if not vacacion_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada"
        )
    
    vacacion = vacacion_result.data[0]
    
    # Verificar permisos (admin o dueño de la solicitud)
    if not current_user.es_admin and vacacion.get('empleado_id') != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver esta solicitud"
        )
    
    # Obtener datos del empleado
    empleado_result = supabase.table("v_empleados_completo").select("*").eq("id", vacacion.get('empleado_id')).execute()
    
    if not empleado_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    
    empleado = empleado_result.data[0]
    
    # Generar PDF
    pdf_buffer = generar_formato_vacaciones(empleado, vacacion)
    
    # Nombre del archivo
    nombre_empleado = empleado.get('nombre_completo', 'empleado').replace(' ', '_')
    fecha = vacacion.get('created_at', '')[:10] if vacacion.get('created_at') else 'fecha'
    filename = f"Solicitud_Vacaciones_{nombre_empleado}_{fecha}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
