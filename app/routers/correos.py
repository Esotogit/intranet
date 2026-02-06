from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.database import supabase, get_admin_client
from app.auth import get_current_admin
from app.config import get_settings

router = APIRouter(prefix="/api/correos", tags=["correos"])
admin_client = get_admin_client()
settings = get_settings()


# ========================================
# MODELOS
# ========================================
class PlantillaCorreo(BaseModel):
    id: Optional[int] = None
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
    asunto: str
    contenido_html: str
    variables_disponibles: Optional[List[str]] = None
    activo: bool = True


class PlantillaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    asunto: Optional[str] = None
    contenido_html: Optional[str] = None
    activo: Optional[bool] = None


class CorreoPrueba(BaseModel):
    destinatario: EmailStr
    asunto: Optional[str] = "Correo de Prueba - Intranet IDS"
    mensaje: Optional[str] = "Este es un correo de prueba para verificar la configuración SMTP."


class ConfigSMTP(BaseModel):
    host: str
    port: int
    user: str
    use_ssl: bool
    email_from: str
    email_from_name: str


# ========================================
# ENDPOINTS - CONFIGURACIÓN
# ========================================
@router.get("/configuracion")
async def obtener_configuracion_smtp(current_user: dict = Depends(get_current_admin)):
    """Obtiene la configuración SMTP actual (sin contraseña)"""
    return {
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "user": settings.smtp_user,
        "use_ssl": settings.smtp_use_ssl,
        "email_from": settings.email_from,
        "email_from_name": settings.email_from_name,
        "configurado": bool(settings.smtp_user and settings.smtp_password)
    }


@router.post("/prueba")
async def enviar_correo_prueba(
    datos: CorreoPrueba,
    current_user: dict = Depends(get_current_admin)
):
    """Envía un correo de prueba para verificar la configuración SMTP"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    if not settings.smtp_user or not settings.smtp_password:
        raise HTTPException(
            status_code=400, 
            detail="No hay credenciales SMTP configuradas en el archivo .env"
        )
    
    contenido_html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background-color: #f3f4f6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
                <div style="background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">✅ Correo de Prueba</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">{settings.email_from_name}</p>
                </div>
                <div style="padding: 30px;">
                    <p style="font-size: 16px; color: #333; margin-bottom: 15px;">¡La configuración SMTP está funcionando correctamente!</p>
                    
                    <div style="background: #f0fdf4; border-radius: 10px; padding: 20px; margin: 20px 0;">
                        <h3 style="margin: 0 0 15px 0; color: #166534; font-size: 14px;">📧 Detalles de la configuración:</h3>
                        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Servidor SMTP:</td>
                                <td style="padding: 6px 0; color: #1e293b; font-weight: 500;">{settings.smtp_host}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Puerto:</td>
                                <td style="padding: 6px 0; color: #1e293b; font-weight: 500;">{settings.smtp_port}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">SSL:</td>
                                <td style="padding: 6px 0; color: #1e293b; font-weight: 500;">{'Sí' if settings.smtp_use_ssl else 'No'}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Remitente:</td>
                                <td style="padding: 6px 0; color: #1e293b; font-weight: 500;">{settings.email_from}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <p style="font-size: 14px; color: #666; margin-top: 20px;">{datos.mensaje}</p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
                    <p style="font-size: 12px; color: #888; margin: 0;">
                        Este correo fue enviado desde la sección de administración de correos de la Intranet.
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    try:
        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = datos.asunto
        mensaje["From"] = f"{settings.email_from_name} <{settings.email_from}>"
        mensaje["To"] = datos.destinatario
        
        parte_html = MIMEText(contenido_html, "html", "utf-8")
        mensaje.attach(parte_html)
        
        print(f"[CORREO] Intentando enviar a {datos.destinatario}")
        print(f"[CORREO] Host: {settings.smtp_host}:{settings.smtp_port}, SSL: {settings.smtp_use_ssl}")
        print(f"[CORREO] User: {settings.smtp_user}")
        
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(mensaje)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(mensaje)
        
        print(f"[CORREO] ✅ Enviado correctamente a {datos.destinatario}")
        return {
            "success": True,
            "message": f"Correo enviado correctamente a {datos.destinatario}",
            "destinatario": datos.destinatario
        }
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"[CORREO] ❌ Error autenticación: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Error de autenticación SMTP: Verifica usuario y contraseña. {str(e)}"
        )
    except smtplib.SMTPConnectError as e:
        print(f"[CORREO] ❌ Error conexión: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo conectar al servidor SMTP: {str(e)}"
        )
    except Exception as e:
        print(f"[CORREO] ❌ Error general: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error al enviar correo: {type(e).__name__}: {str(e)}"
        )


# ========================================
# ENDPOINTS - PLANTILLAS
# ========================================
@router.get("/plantillas", response_model=List[dict])
async def listar_plantillas(current_user: dict = Depends(get_current_admin)):
    """Lista todas las plantillas de correo"""
    result = admin_client.table("plantillas_correo").select("*").order("nombre").execute()
    return result.data


@router.get("/plantillas/{codigo}")
async def obtener_plantilla(
    codigo: str,
    current_user: dict = Depends(get_current_admin)
):
    """Obtiene una plantilla por su código"""
    result = admin_client.table("plantillas_correo").select("*").eq("codigo", codigo).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    return result.data[0]


@router.patch("/plantillas/{codigo}")
async def actualizar_plantilla(
    codigo: str,
    datos: PlantillaUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """Actualiza una plantilla de correo"""
    # Verificar que existe
    existing = admin_client.table("plantillas_correo").select("id").eq("codigo", codigo).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    # Preparar datos para actualizar
    update_data = {k: v for k, v in datos.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")
    
    result = admin_client.table("plantillas_correo").update(update_data).eq("codigo", codigo).execute()
    
    return result.data[0]


@router.post("/plantillas/{codigo}/preview")
async def preview_plantilla(
    codigo: str,
    current_user: dict = Depends(get_current_admin)
):
    """Genera una vista previa de la plantilla con datos de ejemplo"""
    result = admin_client.table("plantillas_correo").select("*").eq("codigo", codigo).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    
    plantilla = result.data[0]
    
    # Datos de ejemplo para reemplazar
    datos_ejemplo = {
        "nombre": "Juan",
        "apellidos": "Pérez García",
        "periodo": "1ra Quincena",
        "mes": "01",
        "mes_nombre": "Enero",
        "anio": "2026",
        "company_name": settings.company_name or "Intranet IDS",
        "app_url": settings.app_url or "https://intranet.ejemplo.com",
        "fecha_inicio": "2026-01-20",
        "fecha_fin": "2026-01-24",
        "dias_solicitados": "5",
        "fechas": "📅 2026-01-20, 📅 2026-01-21, 📅 2026-01-22",
        "comentario_html": '<div style="background: #f8fafc; border-left: 4px solid #10b981; padding: 12px 16px; margin: 20px 0;"><p style="margin: 0; font-size: 12px; color: #64748b; font-weight: 600;">COMENTARIO:</p><p style="margin: 8px 0 0 0; color: #334155;">Disfruta tus vacaciones.</p></div>',
        "titulo": "Reunión General de Empleados",
        "contenido": "Se convoca a todos los empleados a la reunión general que se llevará a cabo el próximo viernes a las 10:00 AM en la sala de conferencias."
    }
    
    # Reemplazar variables en asunto y contenido
    asunto_preview = plantilla["asunto"]
    contenido_preview = plantilla["contenido_html"]
    
    for var, valor in datos_ejemplo.items():
        asunto_preview = asunto_preview.replace(f"{{{var}}}", str(valor))
        contenido_preview = contenido_preview.replace(f"{{{var}}}", str(valor))
    
    return {
        "asunto": asunto_preview,
        "contenido_html": contenido_preview,
        "variables_usadas": plantilla.get("variables_disponibles", [])
    }


@router.post("/plantillas/{codigo}/enviar-prueba")
async def enviar_plantilla_prueba(
    codigo: str,
    datos: CorreoPrueba,
    current_user: dict = Depends(get_current_admin)
):
    """Envía una plantilla con datos de ejemplo como correo de prueba"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    # Obtener preview
    preview = await preview_plantilla(codigo, current_user)
    
    if not settings.smtp_user or not settings.smtp_password:
        raise HTTPException(status_code=400, detail="No hay credenciales SMTP configuradas")
    
    try:
        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = f"[PRUEBA] {preview['asunto']}"
        mensaje["From"] = f"{settings.email_from_name} <{settings.email_from}>"
        mensaje["To"] = datos.destinatario
        
        parte_html = MIMEText(preview["contenido_html"], "html", "utf-8")
        mensaje.attach(parte_html)
        
        print(f"[CORREO PLANTILLA] Enviando '{codigo}' a {datos.destinatario}")
        
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(mensaje)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(mensaje)
        
        print(f"[CORREO PLANTILLA] ✅ Enviado correctamente")
        return {
            "success": True,
            "message": f"Plantilla enviada correctamente a {datos.destinatario}"
        }
        
    except Exception as e:
        print(f"[CORREO PLANTILLA] ❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al enviar: {type(e).__name__}: {str(e)}")


@router.post("/plantillas/{codigo}/restaurar")
async def restaurar_plantilla(
    codigo: str,
    current_user: dict = Depends(get_current_admin)
):
    """Restaura una plantilla a su versión original"""
    # Por ahora solo retorna mensaje - la versión original está en el SQL
    return {
        "message": "Para restaurar la plantilla original, ejecuta el SQL de plantillas_correo.sql",
        "nota": "Esto sobrescribirá los cambios realizados"
    }
