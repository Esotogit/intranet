from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import date
from app.database import supabase, get_admin_client
from app.auth import get_current_user, get_current_admin, get_inventario_user
from app.models import (
    EquipoCreate, EquipoUpdate, Equipo, EquipoCompleto,
    AsignacionEquipo, EstadoEquipo, TipoEquipo
)

router = APIRouter(prefix="/api/inventario", tags=["inventario"])

# Cliente admin para operaciones de escritura (bypass RLS)
admin_client = get_admin_client()


@router.get("/", response_model=List[dict])
async def listar_equipos(
    tipo: Optional[TipoEquipo] = None,
    estado: Optional[EstadoEquipo] = None,
    empleado_id: Optional[str] = None,
    current_user: dict = Depends(get_inventario_user)
):
    """Lista todos los equipos con filtros opcionales"""
    query = admin_client.table("equipos").select(
        "*, empleados(nombre, apellidos), marcas(nombre)"
    ).order("created_at", desc=True)
    
    if tipo:
        query = query.eq("tipo", tipo.value)
    if estado:
        query = query.eq("estado", estado.value)
    if empleado_id:
        query = query.eq("empleado_id", empleado_id)
    
    response = query.execute()
    
    print(f"[DEBUG] Equipos encontrados: {len(response.data)}")
    
    # Formatear respuesta con nombre del empleado y marca
    equipos = []
    for eq in response.data:
        empleado = eq.pop("empleados", None)
        marca_obj = eq.pop("marcas", None)
        eq["empleado_nombre"] = f"{empleado['nombre']} {empleado['apellidos']}" if empleado else None
        eq["marca"] = marca_obj["nombre"] if marca_obj else None
        equipos.append(eq)
    
    return equipos


@router.get("/disponibles", response_model=List[dict])
async def listar_equipos_disponibles(
    tipo: Optional[TipoEquipo] = None,
    current_user: dict = Depends(get_inventario_user)
):
    """Lista equipos disponibles para asignación"""
    query = admin_client.table("equipos").select("*").eq("estado", "disponible")
    
    if tipo:
        query = query.eq("tipo", tipo.value)
    
    response = query.execute()
    return response.data


@router.get("/estadisticas")
async def obtener_estadisticas(current_user: dict = Depends(get_inventario_user)):
    """Obtiene estadísticas del inventario"""
    # Total por estado
    response = admin_client.table("equipos").select("estado").execute()
    
    stats = {
        "total": len(response.data),
        "disponibles": 0,
        "asignados": 0,
        "en_reparacion": 0,
        "baja": 0,
        "por_tipo": {}
    }
    
    for eq in response.data:
        estado = eq.get("estado", "disponible")
        if estado == "disponible":
            stats["disponibles"] += 1
        elif estado == "asignado":
            stats["asignados"] += 1
        elif estado == "en_reparacion":
            stats["en_reparacion"] += 1
        elif estado == "baja":
            stats["baja"] += 1
    
    # Total por tipo
    response_tipos = admin_client.table("equipos").select("tipo").execute()
    for eq in response_tipos.data:
        tipo = eq.get("tipo", "otro")
        stats["por_tipo"][tipo] = stats["por_tipo"].get(tipo, 0) + 1
    
    return stats


@router.get("/{equipo_id}")
async def obtener_equipo(
    equipo_id: str,
    current_user: dict = Depends(get_inventario_user)
):
    """Obtiene un equipo por ID"""
    response = admin_client.table("equipos").select(
        "*, empleados(nombre, apellidos)"
    ).eq("id", equipo_id).single().execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    equipo = response.data
    empleado = equipo.pop("empleados", None)
    equipo["empleado_nombre"] = f"{empleado['nombre']} {empleado['apellidos']}" if empleado else None
    
    return equipo


@router.post("/")
async def crear_equipo(
    equipo: EquipoCreate,
    current_user: dict = Depends(get_inventario_user)
):
    """Crea un nuevo equipo"""
    # Verificar número de serie único si se proporciona
    if equipo.numero_serie:
        existing = admin_client.table("equipos").select("id").eq(
            "numero_serie", equipo.numero_serie
        ).execute()
        if existing.data:
            raise HTTPException(
                status_code=400, 
                detail="Ya existe un equipo con ese número de serie"
            )
    
    data = equipo.model_dump(exclude_none=True)
    
    print(f"[DEBUG] Datos recibidos del modelo: {data}")
    
    # Si no viene estado, establecer disponible por defecto
    if "estado" not in data:
        data["estado"] = "disponible"
    
    # Convertir enum a string
    if "tipo" in data:
        data["tipo"] = data["tipo"].value if hasattr(data["tipo"], "value") else data["tipo"]
    if "estado" in data:
        data["estado"] = data["estado"].value if hasattr(data["estado"], "value") else data["estado"]
    
    # Convertir Decimal a float para JSON
    if "costo" in data and data["costo"]:
        data["costo"] = float(data["costo"])
    
    # Convertir date a string
    if "fecha_compra" in data and data["fecha_compra"]:
        data["fecha_compra"] = str(data["fecha_compra"])
    
    # Si tiene empleado_id, establecer fecha_asignacion
    if data.get("empleado_id") and data.get("estado") == "asignado":
        data["fecha_asignacion"] = str(date.today())
    
    print(f"[DEBUG] Datos a insertar: {data}")
    
    # Usar admin_client para bypass RLS
    response = admin_client.table("equipos").insert(data).execute()
    
    print(f"[DEBUG] Respuesta de Supabase: {response.data}")
    
    return response.data[0]


@router.put("/{equipo_id}")
async def actualizar_equipo(
    equipo_id: str,
    equipo: EquipoUpdate,
    current_user: dict = Depends(get_inventario_user)
):
    """Actualiza un equipo"""
    # Verificar que existe
    existing = admin_client.table("equipos").select("id").eq("id", equipo_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    data = equipo.model_dump(exclude_none=True)
    
    # Convertir enums a strings
    if "tipo" in data:
        data["tipo"] = data["tipo"].value if hasattr(data["tipo"], "value") else data["tipo"]
    if "estado" in data:
        data["estado"] = data["estado"].value if hasattr(data["estado"], "value") else data["estado"]
    
    # Convertir Decimal a float
    if "costo" in data and data["costo"]:
        data["costo"] = float(data["costo"])
    
    # Convertir date a string
    if "fecha_compra" in data and data["fecha_compra"]:
        data["fecha_compra"] = str(data["fecha_compra"])
    
    if data:
        response = admin_client.table("equipos").update(data).eq("id", equipo_id).execute()
        return response.data[0]
    
    return {"message": "No hay cambios"}


@router.post("/{equipo_id}/asignar")
async def asignar_equipo(
    equipo_id: str,
    asignacion: AsignacionEquipo,
    current_user: dict = Depends(get_inventario_user)
):
    """Asigna un equipo a un empleado"""
    # Verificar que el equipo existe y está disponible
    equipo = admin_client.table("equipos").select("*").eq("id", equipo_id).single().execute()
    if not equipo.data:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    if equipo.data["estado"] != "disponible":
        raise HTTPException(
            status_code=400, 
            detail=f"El equipo no está disponible (estado: {equipo.data['estado']})"
        )
    
    # Verificar que el empleado existe
    empleado = admin_client.table("empleados").select("id").eq(
        "id", asignacion.empleado_id
    ).single().execute()
    if not empleado.data:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    fecha = asignacion.fecha_asignacion or date.today()
    
    # Actualizar equipo
    update_data = {
        "empleado_id": asignacion.empleado_id,
        "fecha_asignacion": str(fecha),
        "estado": "asignado"
    }
    if asignacion.notas:
        update_data["notas"] = asignacion.notas
    
    admin_client.table("equipos").update(update_data).eq("id", equipo_id).execute()
    
    # Registrar en historial
    historial_data = {
        "equipo_id": equipo_id,
        "empleado_id": asignacion.empleado_id,
        "fecha_asignacion": str(fecha),
        "notas": asignacion.notas
    }
    admin_client.table("historial_equipos").insert(historial_data).execute()
    
    return {"message": "Equipo asignado exitosamente"}


@router.post("/{equipo_id}/desasignar")
async def desasignar_equipo(
    equipo_id: str,
    notas: Optional[str] = None,
    current_user: dict = Depends(get_inventario_user)
):
    """Desasigna un equipo de un empleado"""
    # Verificar que el equipo existe y está asignado
    equipo = admin_client.table("equipos").select("*").eq("id", equipo_id).single().execute()
    if not equipo.data:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    if equipo.data["estado"] != "asignado":
        raise HTTPException(status_code=400, detail="El equipo no está asignado")
    
    empleado_id = equipo.data.get("empleado_id")
    
    # Validar que realmente tiene un empleado asignado
    if not empleado_id:
        # El estado dice asignado pero no tiene empleado - corregir inconsistencia
        admin_client.table("equipos").update({
            "estado": "disponible",
            "fecha_asignacion": None
        }).eq("id", equipo_id).execute()
        return {"message": "Estado del equipo corregido a disponible"}
    
    # Actualizar historial con fecha de devolución
    try:
        admin_client.table("historial_equipos").update({
            "fecha_devolucion": str(date.today()),
            "notas": notas
        }).eq("equipo_id", equipo_id).eq(
            "empleado_id", empleado_id
        ).is_("fecha_devolucion", "null").execute()
    except Exception as e:
        print(f"[WARNING] Error actualizando historial: {e}")
    
    # Actualizar equipo
    admin_client.table("equipos").update({
        "empleado_id": None,
        "fecha_asignacion": None,
        "estado": "disponible",
        "notas": notas
    }).eq("id", equipo_id).execute()
    
    return {"message": "Equipo desasignado exitosamente"}


@router.get("/{equipo_id}/historial")
async def obtener_historial_equipo(
    equipo_id: str,
    current_user: dict = Depends(get_inventario_user)
):
    """Obtiene el historial de asignaciones de un equipo"""
    response = admin_client.table("historial_equipos").select(
        "*, empleados(nombre, apellidos)"
    ).eq("equipo_id", equipo_id).order("fecha_asignacion", desc=True).execute()
    
    historial = []
    for h in response.data:
        empleado = h.pop("empleados", None)
        h["empleado_nombre"] = f"{empleado['nombre']} {empleado['apellidos']}" if empleado else None
        historial.append(h)
    
    return historial


@router.get("/empleado/{empleado_id}/equipos")
async def obtener_equipos_empleado(
    empleado_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Obtiene los equipos asignados a un empleado"""
    # Verificar permisos (admin o el mismo empleado)
    if not current_user.es_admin and current_user.user_id != empleado_id:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    response = admin_client.table("equipos").select("*").eq(
        "empleado_id", empleado_id
    ).eq("estado", "asignado").execute()
    
    return response.data


@router.delete("/{equipo_id}")
async def eliminar_equipo(
    equipo_id: str,
    current_user: dict = Depends(get_inventario_user)
):
    """Elimina un equipo (solo si está disponible o dado de baja)"""
    # Verificar estado
    equipo = admin_client.table("equipos").select("estado").eq("id", equipo_id).single().execute()
    if not equipo.data:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    if equipo.data["estado"] == "asignado":
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar un equipo asignado. Desasígnalo primero."
        )
    
    # Eliminar historial primero
    admin_client.table("historial_equipos").delete().eq("equipo_id", equipo_id).execute()
    
    # Eliminar equipo
    admin_client.table("equipos").delete().eq("id", equipo_id).execute()
    
    return {"message": "Equipo eliminado"}


# ========================================
# RESPONSIVA DE EQUIPO
# ========================================
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.pdf_generator import generar_responsiva_equipo
from app.services.email_service import enviar_correo


class DatosResponsiva(BaseModel):
    descripcion_equipo: str = "Prestamo"
    procesador: str = ""
    pantalla: str = ""
    memoria_ram: str = ""
    disco_duro: str = ""
    dvd_rw: str = "NO"
    sistema_operativo: str = ""
    nombre_entrega: str = "Nelson Rios Rengifo"


@router.post("/{equipo_id}/responsiva/generar")
async def generar_responsiva(
    equipo_id: str,
    datos: DatosResponsiva,
    current_user: dict = Depends(get_inventario_user)
):
    """Genera el PDF de responsiva para un equipo asignado"""
    
    # Obtener datos del equipo
    equipo_result = admin_client.table("equipos").select("*").eq("id", equipo_id).execute()
    
    if not equipo_result.data:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    equipo = equipo_result.data[0]
    
    if not equipo.get("empleado_id"):
        raise HTTPException(status_code=400, detail="El equipo no está asignado a ningún empleado")
    
    # Obtener datos del empleado
    empleado_result = admin_client.table("v_empleados_completo").select("*").eq("id", equipo["empleado_id"]).execute()
    
    if not empleado_result.data:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    empleado = empleado_result.data[0]
    
    # Generar PDF
    pdf_buffer = generar_responsiva_equipo(
        empleado=empleado,
        equipo=equipo,
        datos_responsiva=datos.model_dump(),
        nombre_entrega=datos.nombre_entrega
    )
    
    # Nombre del archivo
    nombre_archivo = f"Responsiva_{empleado['nombre']}_{empleado['apellidos']}_{date.today().year}.pdf"
    nombre_archivo = nombre_archivo.replace(" ", "_")
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"}
    )


@router.post("/{equipo_id}/responsiva/enviar")
async def enviar_responsiva_correo(
    equipo_id: str,
    datos: DatosResponsiva,
    current_user: dict = Depends(get_inventario_user)
):
    """Genera y envía el PDF de responsiva por correo al empleado y al admin"""
    
    # Obtener datos del equipo
    equipo_result = admin_client.table("equipos").select("*").eq("id", equipo_id).execute()
    
    if not equipo_result.data:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    equipo = equipo_result.data[0]
    
    if not equipo.get("empleado_id"):
        raise HTTPException(status_code=400, detail="El equipo no está asignado a ningún empleado")
    
    # Obtener datos del empleado
    empleado_result = admin_client.table("v_empleados_completo").select("*").eq("id", equipo["empleado_id"]).execute()
    
    if not empleado_result.data:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    empleado = empleado_result.data[0]
    
    # Obtener email del admin actual
    admin_result = admin_client.table("empleados").select("email, nombre, apellidos").eq("id", current_user.user_id).execute()
    admin_email = admin_result.data[0]["email"] if admin_result.data else None
    admin_nombre = f"{admin_result.data[0]['nombre']} {admin_result.data[0]['apellidos']}" if admin_result.data else "Administrador"
    
    # Generar PDF
    pdf_buffer = generar_responsiva_equipo(
        empleado=empleado,
        equipo=equipo,
        datos_responsiva=datos.model_dump(),
        nombre_entrega=datos.nombre_entrega
    )
    
    # Preparar contenido del correo
    nombre_completo = f"{empleado['nombre']} {empleado['apellidos']}"
    asunto = f"📋 Responsiva de Equipo - {equipo.get('modelo', '')} {equipo.get('marca', '')}"
    
    contenido_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background-color: #f3f4f6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
                
                <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0093b0 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 22px;">📋 Responsiva de Equipo</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">Informática y Desarrollo en Sistemas</p>
                </div>
                
                <div style="padding: 30px;">
                    <p style="font-size: 16px; color: #333;">Hola <strong>{empleado['nombre']}</strong>,</p>
                    <p style="font-size: 15px; color: #555; line-height: 1.6;">
                        Se ha generado la responsiva de equipo para el siguiente dispositivo:
                    </p>
                    
                    <div style="background: #f8fafc; border-radius: 10px; padding: 20px; margin: 20px 0;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; color: #64748b; font-size: 13px;">Tipo:</td>
                                <td style="padding: 8px 0; color: #1e293b; font-weight: 600;">{equipo.get('tipo', '').capitalize()}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #64748b; font-size: 13px;">Marca/Modelo:</td>
                                <td style="padding: 8px 0; color: #1e293b; font-weight: 600;">{equipo.get('marca', '')} {equipo.get('modelo', '')}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #64748b; font-size: 13px;">No. Serie:</td>
                                <td style="padding: 8px 0; color: #1e293b; font-weight: 600;">{equipo.get('numero_serie', '')}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <p style="font-size: 13px; color: #888; line-height: 1.6;">
                        Adjunto encontrarás el documento de responsiva en formato PDF. Por favor, revísalo y fírmalo.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
                    
                    <p style="font-size: 13px; color: #888; margin: 0;">
                        Saludos,<br>
                        <strong style="color: #1e3a5f;">{admin_nombre}</strong>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Enviar correos
    resultados = {"empleado": None, "admin": None}
    
    # Al empleado
    if empleado.get("email"):
        resultado_emp = enviar_correo_con_adjunto(
            destinatario=empleado["email"],
            asunto=asunto,
            contenido_html=contenido_html,
            pdf_buffer=pdf_buffer,
            nombre_archivo=f"Responsiva_{nombre_completo.replace(' ', '_')}_{date.today().year}.pdf"
        )
        resultados["empleado"] = resultado_emp
    
    # Regenerar buffer para el admin
    pdf_buffer_admin = generar_responsiva_equipo(
        empleado=empleado,
        equipo=equipo,
        datos_responsiva=datos.model_dump(),
        nombre_entrega=datos.nombre_entrega
    )
    
    # Al admin
    if admin_email:
        resultado_admin = enviar_correo_con_adjunto(
            destinatario=admin_email,
            asunto=f"[Copia] {asunto}",
            contenido_html=contenido_html.replace(f"Hola <strong>{empleado['nombre']}</strong>", 
                                                   f"Hola <strong>{admin_nombre}</strong> (copia de responsiva enviada a {nombre_completo})"),
            pdf_buffer=pdf_buffer_admin,
            nombre_archivo=f"Responsiva_{nombre_completo.replace(' ', '_')}_{date.today().year}.pdf"
        )
        resultados["admin"] = resultado_admin
    
    return {
        "message": "Responsiva enviada correctamente",
        "enviado_a_empleado": empleado.get("email"),
        "enviado_a_admin": admin_email,
        "resultados": resultados
    }


def enviar_correo_con_adjunto(destinatario: str, asunto: str, contenido_html: str, pdf_buffer, nombre_archivo: str):
    """Envía un correo con un PDF adjunto"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.mime.application import MIMEApplication
    from app.config import get_settings
    
    settings = get_settings()
    
    if not settings.smtp_user or not settings.smtp_password:
        return {"success": True, "simulated": True, "message": "Email simulado - sin credenciales SMTP"}
    
    try:
        mensaje = MIMEMultipart()
        mensaje["Subject"] = asunto
        mensaje["From"] = f"{settings.email_from_name} <{settings.email_from}>"
        mensaje["To"] = destinatario
        
        # Contenido HTML
        parte_html = MIMEText(contenido_html, "html", "utf-8")
        mensaje.attach(parte_html)
        
        # Adjuntar PDF
        pdf_buffer.seek(0)
        adjunto = MIMEApplication(pdf_buffer.read(), _subtype="pdf")
        adjunto.add_header("Content-Disposition", "attachment", filename=nombre_archivo)
        mensaje.attach(adjunto)
        
        # Enviar
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(mensaje)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(mensaje)
        
        return {"success": True, "message": "Email enviado correctamente"}
        
    except Exception as e:
        print(f"[ERROR] Enviando email con adjunto: {str(e)}")
        return {"success": False, "message": str(e)}
