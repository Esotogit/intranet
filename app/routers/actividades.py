from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import date, timedelta

from app.database import supabase
from app.models import (
    Actividad,
    ActividadCreate,
    ActividadUpdate,
    ActividadSemanalCreate,
    ResumenSemanal,
    ResumenMensual,
    DiaSemana,
    TokenData
)
from app.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/api/actividades", tags=["Actividades"])


def get_dia_semana(fecha: date) -> str:
    """Obtiene el día de la semana en formato L, M, X, J, V, S, D"""
    dias = ['L', 'M', 'X', 'J', 'V', 'S', 'D']
    return dias[fecha.weekday()]


def get_lunes_semana(fecha: date) -> date:
    """Obtiene el lunes de la semana de una fecha dada"""
    return fecha - timedelta(days=fecha.weekday())


@router.get("/semana", response_model=List[Actividad])
async def obtener_semana(
    fecha: Optional[date] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Obtener actividades de una semana (por defecto la actual)"""
    
    if not fecha:
        fecha = date.today()
    
    lunes = get_lunes_semana(fecha)
    viernes = lunes + timedelta(days=4)
    
    result = supabase.table("actividades").select("*").eq("empleado_id", current_user.user_id).gte("fecha", lunes.isoformat()).lte("fecha", viernes.isoformat()).order("fecha").execute()
    
    return result.data


@router.post("/semana", status_code=status.HTTP_201_CREATED)
async def guardar_semana(
    datos: ActividadSemanalCreate,
    current_user: TokenData = Depends(get_current_user)
):
    """Guardar actividades de toda la semana"""
    
    lunes = get_lunes_semana(datos.semana_inicio)
    
    # Preparar datos para upsert
    actividades_data = []
    for actividad in datos.actividades:
        act_dict = {
            "empleado_id": current_user.user_id,
            "fecha": actividad.fecha.isoformat(),
            "dia_semana": get_dia_semana(actividad.fecha),
            "hora_entrada": actividad.hora_entrada.isoformat() if actividad.hora_entrada else None,
            "hora_salida": actividad.hora_salida.isoformat() if actividad.hora_salida else None,
            "descripcion": actividad.descripcion,
            "ubicacion_id": actividad.ubicacion_id
        }
        actividades_data.append(act_dict)
    
    # Usar upsert para insertar o actualizar
    result = supabase.table("actividades").upsert(
        actividades_data,
        on_conflict="empleado_id,fecha"
    ).execute()
    
    return {"message": f"Se guardaron {len(result.data)} actividades"}


@router.get("/mes/{anio}/{mes}", response_model=List[Actividad])
async def obtener_mes(
    anio: int,
    mes: int,
    current_user: TokenData = Depends(get_current_user)
):
    """Obtener actividades de un mes"""
    
    fecha_inicio = date(anio, mes, 1)
    
    # Calcular último día del mes
    if mes == 12:
        fecha_fin = date(anio + 1, 1, 1) - timedelta(days=1)
    else:
        fecha_fin = date(anio, mes + 1, 1) - timedelta(days=1)
    
    result = supabase.table("actividades").select("*").eq("empleado_id", current_user.user_id).gte("fecha", fecha_inicio.isoformat()).lte("fecha", fecha_fin.isoformat()).order("fecha").execute()
    
    return result.data


@router.put("/{actividad_id}", response_model=Actividad)
async def actualizar_actividad(
    actividad_id: str,
    actividad: ActividadUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    """Actualizar una actividad específica"""
    
    update_data = {k: v for k, v in actividad.model_dump().items() if v is not None}
    
    if "hora_entrada" in update_data and update_data["hora_entrada"]:
        update_data["hora_entrada"] = update_data["hora_entrada"].isoformat()
    if "hora_salida" in update_data and update_data["hora_salida"]:
        update_data["hora_salida"] = update_data["hora_salida"].isoformat()
    
    result = supabase.table("actividades").update(update_data).eq("id", actividad_id).eq("empleado_id", current_user.user_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actividad no encontrada"
        )
    
    return result.data[0]


# ===========================================
# RUTAS DE ADMINISTRADOR
# ===========================================

@router.get("/admin/sin-captura", response_model=List[dict])
async def empleados_sin_captura(
    current_user: TokenData = Depends(get_current_admin)
):
    """Obtener empleados que no han capturado actividades esta semana"""
    
    result = supabase.table("v_empleados_sin_captura").select("*").execute()
    
    return result.data


@router.get("/admin/resumen-semanal", response_model=List[ResumenSemanal])
async def resumen_semanal_admin(
    fecha: Optional[date] = None,
    current_user: TokenData = Depends(get_current_admin)
):
    """Obtener resumen semanal de todos los empleados"""
    
    if not fecha:
        fecha = date.today()
    
    lunes = get_lunes_semana(fecha)
    
    result = supabase.table("v_resumen_semanal").select("*").eq("semana_inicio", lunes.isoformat()).execute()
    
    return result.data


@router.get("/admin/resumen-mensual", response_model=List[ResumenMensual])
async def resumen_mensual_admin(
    anio: int,
    mes: int,
    current_user: TokenData = Depends(get_current_admin)
):
    """Obtener resumen mensual de todos los empleados"""
    
    result = supabase.table("v_resumen_mensual").select("*").eq("anio", anio).eq("mes", mes).execute()
    
    return result.data


@router.get("/admin/seguimiento-semanal")
async def seguimiento_semanal_admin(
    fecha_inicio: Optional[date] = None,
    current_user: TokenData = Depends(get_current_admin)
):
    """Obtener seguimiento semanal detallado de todos los empleados"""
    
    if not fecha_inicio:
        fecha_inicio = get_lunes_semana(date.today())
    else:
        # Asegurar que sea lunes
        fecha_inicio = get_lunes_semana(fecha_inicio)
    
    fecha_fin = fecha_inicio + timedelta(days=4)  # Viernes
    
    # Obtener todos los empleados activos
    empleados_result = supabase.table("empleados").select(
        "id, nombre, apellidos, puesto:puestos(nombre)"
    ).eq("activo", True).execute()
    
    if not empleados_result.data:
        return []
    
    # Obtener actividades de la semana
    actividades_result = supabase.table("actividades").select(
        "empleado_id, fecha, horas_trabajadas"
    ).gte("fecha", fecha_inicio.isoformat()).lte("fecha", fecha_fin.isoformat()).execute()
    
    # Crear diccionario de actividades por empleado y día
    actividades_por_empleado = {}
    for act in actividades_result.data:
        emp_id = act["empleado_id"]
        if emp_id not in actividades_por_empleado:
            actividades_por_empleado[emp_id] = {}
        
        fecha_act = act["fecha"]
        if isinstance(fecha_act, str):
            fecha_obj = date.fromisoformat(fecha_act)
        else:
            fecha_obj = fecha_act
        
        # Determinar qué día de la semana es (0=lunes, 4=viernes)
        dia_idx = (fecha_obj - fecha_inicio).days
        if 0 <= dia_idx <= 4:
            dias_nombre = ["lunes", "martes", "miercoles", "jueves", "viernes"]
            actividades_por_empleado[emp_id][dias_nombre[dia_idx]] = float(act.get("horas_trabajadas", 0) or 0)
    
    # Construir respuesta
    resultado = []
    for emp in empleados_result.data:
        emp_id = emp["id"]
        puesto_nombre = ""
        if emp.get("puesto") and isinstance(emp["puesto"], dict):
            puesto_nombre = emp["puesto"].get("nombre", "")
        
        dias = actividades_por_empleado.get(emp_id, {})
        
        resultado.append({
            "empleado_id": emp_id,
            "nombre": emp["nombre"],
            "apellidos": emp["apellidos"],
            "puesto": puesto_nombre,
            "dias": {
                "lunes": dias.get("lunes", 0),
                "martes": dias.get("martes", 0),
                "miercoles": dias.get("miercoles", 0),
                "jueves": dias.get("jueves", 0),
                "viernes": dias.get("viernes", 0)
            }
        })
    
    return resultado


@router.get("/admin/empleado/{empleado_id}/mes/{anio}/{mes}", response_model=List[Actividad])
async def actividades_empleado(
    empleado_id: str,
    anio: int,
    mes: int,
    current_user: TokenData = Depends(get_current_admin)
):
    """Obtener actividades de un empleado específico (admin)"""
    
    fecha_inicio = date(anio, mes, 1)
    
    if mes == 12:
        fecha_fin = date(anio + 1, 1, 1) - timedelta(days=1)
    else:
        fecha_fin = date(anio, mes + 1, 1) - timedelta(days=1)
    
    result = supabase.table("actividades").select(
        "*, ubicacion:ubicaciones(codigo, nombre)"
    ).eq("empleado_id", empleado_id).gte("fecha", fecha_inicio.isoformat()).lte("fecha", fecha_fin.isoformat()).order("fecha").execute()
    
    return result.data


@router.post("/admin/enviar-recordatorios")
async def enviar_recordatorios(
    fecha_inicio: Optional[date] = None,
    current_user: TokenData = Depends(get_current_admin)
):
    """Envía recordatorio por email a empleados que no han completado sus actividades"""
    from app.services.email_service import enviar_recordatorio_actividades
    
    if not fecha_inicio:
        fecha_inicio = get_lunes_semana(date.today())
    else:
        fecha_inicio = get_lunes_semana(fecha_inicio)
    
    fecha_fin = fecha_inicio + timedelta(days=4)
    
    # Obtener todos los empleados activos con su email
    empleados_result = supabase.table("empleados").select(
        "id, nombre, apellidos, email"
    ).eq("activo", True).execute()
    
    if not empleados_result.data:
        return {"message": "No hay empleados activos", "enviados": 0}
    
    # Obtener actividades de la semana
    actividades_result = supabase.table("actividades").select(
        "empleado_id, fecha, horas_trabajadas"
    ).gte("fecha", fecha_inicio.isoformat()).lte("fecha", fecha_fin.isoformat()).execute()
    
    # Contar días capturados por empleado
    dias_por_empleado = {}
    for act in actividades_result.data:
        emp_id = act["empleado_id"]
        horas = float(act.get("horas_trabajadas", 0) or 0)
        if horas > 0:
            dias_por_empleado[emp_id] = dias_por_empleado.get(emp_id, 0) + 1
    
    # Filtrar empleados que no han completado (menos de 5 días)
    empleados_pendientes = []
    for emp in empleados_result.data:
        dias = dias_por_empleado.get(emp["id"], 0)
        if dias < 5:  # No ha completado la semana
            empleados_pendientes.append(emp)
    
    if not empleados_pendientes:
        return {
            "message": "Todos los empleados han completado sus actividades",
            "enviados": 0,
            "total_empleados": len(empleados_result.data)
        }
    
    # Formatear semana para el mensaje
    meses = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
    semana_str = f"{fecha_inicio.day}-{meses[fecha_inicio.month-1]} al {fecha_fin.day}-{meses[fecha_fin.month-1]}"
    
    # Enviar recordatorios
    resultado = enviar_recordatorio_actividades(empleados_pendientes, semana_str)
    
    return {
        "message": f"Recordatorios enviados a {resultado['enviados']} empleados",
        "enviados": resultado["enviados"],
        "fallidos": resultado["fallidos"],
        "total_pendientes": len(empleados_pendientes),
        "detalles": resultado["detalles"]
    }


@router.get("/admin/test-smtp")
async def test_smtp(
    current_user: TokenData = Depends(get_current_admin)
):
    """Prueba la conexión SMTP"""
    from app.services.email_service import test_smtp_connection
    return test_smtp_connection()


@router.post("/admin/test-email")
async def test_email(
    email_destino: str,
    current_user: TokenData = Depends(get_current_admin)
):
    """Envía un email de prueba"""
    from app.services.email_service import enviar_correo
    
    resultado = enviar_correo(
        destinatario=email_destino,
        asunto="🧪 Email de prueba - Intranet IDS",
        contenido_html="""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #0093b0;">✅ Email de Prueba Exitoso</h2>
            <p>Si estás viendo este mensaje, la configuración SMTP está funcionando correctamente.</p>
            <p style="color: #666; font-size: 12px;">Enviado desde Intranet IDS</p>
        </body>
        </html>
        """,
        contenido_texto="Email de prueba exitoso. La configuración SMTP está funcionando."
    )
    
    return {
        "destino": email_destino,
        "resultado": resultado
    }
