from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from datetime import date, timedelta
from typing import Optional

from app.database import supabase
from app.models import TokenData
from app.auth import get_current_user, get_current_admin
from app.services.pdf_generator import generar_reporte_mensual, generar_reporte_semanal

router = APIRouter(prefix="/api/reportes", tags=["Reportes PDF"])


def get_lunes_semana(fecha: date) -> date:
    """Obtiene el lunes de la semana de una fecha dada"""
    return fecha - timedelta(days=fecha.weekday())


@router.get("/mi-reporte-mensual/{anio}/{mes}")
async def mi_reporte_mensual(
    anio: int,
    mes: int,
    current_user: TokenData = Depends(get_current_user)
):
    """Generar mi reporte mensual en PDF"""
    
    # Obtener datos del empleado
    empleado_result = supabase.table("v_empleados_completo").select("*").eq("id", current_user.user_id).execute()
    
    if not empleado_result.data:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    empleado = empleado_result.data[0]
    
    # Obtener actividades del mes
    fecha_inicio = date(anio, mes, 1)
    if mes == 12:
        fecha_fin = date(anio + 1, 1, 1) - timedelta(days=1)
    else:
        fecha_fin = date(anio, mes + 1, 1) - timedelta(days=1)
    
    actividades_result = supabase.table("actividades").select(
        "*, ubicacion:ubicaciones(codigo, nombre)"
    ).eq("empleado_id", current_user.user_id).gte("fecha", fecha_inicio.isoformat()).lte("fecha", fecha_fin.isoformat()).order("fecha").execute()
    
    # Generar PDF
    pdf_buffer = generar_reporte_mensual(
        empleado=empleado,
        actividades=actividades_result.data,
        anio=anio,
        mes=mes
    )
    
    # Nombre del archivo
    nombre_archivo = f"Reporte_{empleado['nombre']}_{empleado['apellidos']}_{anio}_{mes:02d}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={nombre_archivo}"
        }
    )


@router.get("/mi-reporte-semanal")
async def mi_reporte_semanal(
    fecha: Optional[date] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Generar mi reporte semanal en PDF"""
    
    if not fecha:
        fecha = date.today()
    
    lunes = get_lunes_semana(fecha)
    viernes = lunes + timedelta(days=4)
    
    # Obtener datos del empleado
    empleado_result = supabase.table("v_empleados_completo").select("*").eq("id", current_user.user_id).execute()
    
    if not empleado_result.data:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    empleado = empleado_result.data[0]
    
    # Obtener actividades de la semana
    actividades_result = supabase.table("actividades").select(
        "*, ubicacion:ubicaciones(codigo, nombre)"
    ).eq("empleado_id", current_user.user_id).gte("fecha", lunes.isoformat()).lte("fecha", viernes.isoformat()).order("fecha").execute()
    
    # Generar PDF
    pdf_buffer = generar_reporte_semanal(
        empleado=empleado,
        actividades=actividades_result.data,
        semana_inicio=lunes
    )
    
    nombre_archivo = f"Reporte_Semanal_{empleado['nombre']}_{lunes.isoformat()}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={nombre_archivo}"
        }
    )


# ===========================================
# RUTAS DE ADMINISTRADOR
# ===========================================

@router.get("/admin/reporte-mensual/{empleado_id}/{anio}/{mes}")
async def reporte_mensual_empleado(
    empleado_id: str,
    anio: int,
    mes: int,
    current_user: TokenData = Depends(get_current_admin)
):
    """Generar reporte mensual de un empleado (admin)"""
    
    # Obtener datos del empleado
    empleado_result = supabase.table("v_empleados_completo").select("*").eq("id", empleado_id).execute()
    
    if not empleado_result.data:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    empleado = empleado_result.data[0]
    
    # Obtener actividades del mes
    fecha_inicio = date(anio, mes, 1)
    if mes == 12:
        fecha_fin = date(anio + 1, 1, 1) - timedelta(days=1)
    else:
        fecha_fin = date(anio, mes + 1, 1) - timedelta(days=1)
    
    actividades_result = supabase.table("actividades").select(
        "*, ubicacion:ubicaciones(codigo, nombre)"
    ).eq("empleado_id", empleado_id).gte("fecha", fecha_inicio.isoformat()).lte("fecha", fecha_fin.isoformat()).order("fecha").execute()
    
    # Generar PDF
    pdf_buffer = generar_reporte_mensual(
        empleado=empleado,
        actividades=actividades_result.data,
        anio=anio,
        mes=mes
    )
    
    nombre_archivo = f"Reporte_{empleado['nombre']}_{empleado['apellidos']}_{anio}_{mes:02d}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={nombre_archivo}"
        }
    )


@router.get("/admin/reporte-semanal/{empleado_id}")
async def reporte_semanal_empleado(
    empleado_id: str,
    fecha: Optional[date] = None,
    current_user: TokenData = Depends(get_current_admin)
):
    """Generar reporte semanal de un empleado (admin)"""
    
    if not fecha:
        fecha = date.today()
    
    lunes = get_lunes_semana(fecha)
    viernes = lunes + timedelta(days=4)
    
    # Obtener datos del empleado
    empleado_result = supabase.table("v_empleados_completo").select("*").eq("id", empleado_id).execute()
    
    if not empleado_result.data:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    empleado = empleado_result.data[0]
    
    # Obtener actividades de la semana
    actividades_result = supabase.table("actividades").select(
        "*, ubicacion:ubicaciones(codigo, nombre)"
    ).eq("empleado_id", empleado_id).gte("fecha", lunes.isoformat()).lte("fecha", viernes.isoformat()).order("fecha").execute()
    
    # Generar PDF
    pdf_buffer = generar_reporte_semanal(
        empleado=empleado,
        actividades=actividades_result.data,
        semana_inicio=lunes
    )
    
    nombre_archivo = f"Reporte_Semanal_{empleado['nombre']}_{lunes.isoformat()}.pdf"
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={nombre_archivo}"
        }
    )
