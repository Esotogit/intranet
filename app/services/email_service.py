import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import logging

from app.config import get_settings

settings = get_settings()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def enviar_correo(
    destinatario: str,
    asunto: str,
    contenido_html: str,
    contenido_texto: Optional[str] = None
) -> dict:
    """
    Envía un correo electrónico via SMTP.
    Retorna dict con status y mensaje de error si aplica.
    """
    
    # Verificar configuración SMTP
    logger.info(f"=== INICIO ENVÍO EMAIL ===")
    logger.info(f"Destinatario: {destinatario}")
    logger.info(f"Asunto: {asunto}")
    logger.info(f"SMTP Host: {settings.smtp_host}")
    logger.info(f"SMTP Port: {settings.smtp_port}")
    logger.info(f"SMTP User: {settings.smtp_user}")
    logger.info(f"SMTP Password configurado: {'Sí' if settings.smtp_password else 'No'}")
    logger.info(f"SMTP SSL: {settings.smtp_use_ssl}")
    logger.info(f"Email From: {settings.email_from}")
    
    # Si no hay configuración SMTP, simular envío
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("[EMAIL SIMULADO] No hay credenciales SMTP configuradas")
        return {"success": True, "simulated": True, "message": "Email simulado - sin credenciales SMTP"}
    
    try:
        # Crear mensaje
        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = asunto
        mensaje["From"] = f"{settings.email_from_name} <{settings.email_from}>"
        mensaje["To"] = destinatario
        
        # Agregar contenido texto plano
        if contenido_texto:
            parte_texto = MIMEText(contenido_texto, "plain", "utf-8")
            mensaje.attach(parte_texto)
        
        # Agregar contenido HTML
        parte_html = MIMEText(contenido_html, "html", "utf-8")
        mensaje.attach(parte_html)
        
        logger.info(f"Mensaje creado, intentando conexión SMTP...")
        
        # Conectar y enviar
        if settings.smtp_use_ssl:
            # SSL directo (puerto 465)
            logger.info(f"Conectando con SSL a {settings.smtp_host}:{settings.smtp_port}")
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context, timeout=30) as servidor:
                logger.info("Conexión SSL establecida, autenticando...")
                servidor.login(settings.smtp_user, settings.smtp_password)
                logger.info("Autenticación exitosa, enviando mensaje...")
                servidor.sendmail(settings.email_from, destinatario, mensaje.as_string())
                logger.info(f"[EMAIL ENVIADO EXITOSAMENTE] Para: {destinatario}")
        else:
            # STARTTLS (puerto 587)
            logger.info(f"Conectando con STARTTLS a {settings.smtp_host}:{settings.smtp_port}")
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as servidor:
                servidor.starttls()
                logger.info("STARTTLS establecido, autenticando...")
                servidor.login(settings.smtp_user, settings.smtp_password)
                logger.info("Autenticación exitosa, enviando mensaje...")
                servidor.sendmail(settings.email_from, destinatario, mensaje.as_string())
                logger.info(f"[EMAIL ENVIADO EXITOSAMENTE] Para: {destinatario}")
        
        return {"success": True, "simulated": False, "message": "Email enviado correctamente"}
        
    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"Error de autenticación SMTP: {e}"
        logger.error(error_msg)
        return {"success": False, "error": "auth_error", "message": error_msg}
    
    except smtplib.SMTPConnectError as e:
        error_msg = f"Error de conexión SMTP: {e}"
        logger.error(error_msg)
        return {"success": False, "error": "connect_error", "message": error_msg}
    
    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f"Destinatario rechazado: {e}"
        logger.error(error_msg)
        return {"success": False, "error": "recipient_refused", "message": error_msg}
    
    except ssl.SSLError as e:
        error_msg = f"Error SSL: {e}"
        logger.error(error_msg)
        return {"success": False, "error": "ssl_error", "message": error_msg}
    
    except TimeoutError as e:
        error_msg = f"Timeout de conexión: {e}"
        logger.error(error_msg)
        return {"success": False, "error": "timeout", "message": error_msg}
    
    except Exception as e:
        error_msg = f"Error inesperado: {type(e).__name__}: {e}"
        logger.error(error_msg)
        return {"success": False, "error": "unknown", "message": error_msg}


def enviar_correo_multiple(
    destinatarios: List[str],
    asunto: str,
    contenido_html: str,
    contenido_texto: Optional[str] = None
) -> int:
    """Envía un correo a múltiples destinatarios. Retorna cantidad de enviados."""
    
    enviados = 0
    for dest in destinatarios:
        if enviar_correo(dest, asunto, contenido_html, contenido_texto):
            enviados += 1
    return enviados


def enviar_recordatorio_actividades(
    empleados: List[dict],
    semana: str,
    url_sistema: str = None
) -> dict:
    """
    Envía recordatorio de captura de actividades a una lista de empleados.
    Retorna diccionario con resultados.
    """
    
    if url_sistema is None:
        url_sistema = settings.APP_URL
    
    enviados = 0
    fallidos = 0
    detalles = []
    
    for empleado in empleados:
        email = empleado.get('email', '')
        nombre = f"{empleado.get('nombre', '')} {empleado.get('apellidos', '')}".strip()
        
        if not email:
            fallidos += 1
            detalles.append({"nombre": nombre, "status": "sin_email", "error": "No tiene email registrado"})
            continue
        
        asunto = f"📋 Recordatorio: Captura de actividades - Semana {semana}"
        
        contenido_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 0; margin: 0; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0093b0 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">📋 Recordatorio de Actividades</h1>
                </div>
                
                <div style="background: white; padding: 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <p style="font-size: 16px; color: #333;">Hola <strong>{nombre}</strong>,</p>
                    
                    <p style="font-size: 15px; color: #555; line-height: 1.6;">
                        Te recordamos que aún no has completado la captura de tus actividades 
                        de la semana <strong style="color: #0093b0;">{semana}</strong>.
                    </p>
                    
                    <p style="font-size: 15px; color: #555; line-height: 1.6;">
                        Por favor ingresa al sistema para registrar tus horas trabajadas.
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{url_sistema}/actividades" 
                           style="background: linear-gradient(135deg, #0093b0 0%, #007a94 100%); 
                                  color: white; 
                                  padding: 14px 32px; 
                                  text-decoration: none; 
                                  border-radius: 8px; 
                                  font-weight: 600;
                                  font-size: 15px;
                                  display: inline-block;">
                            Capturar Actividades
                        </a>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
                    
                    <p style="font-size: 13px; color: #888; margin: 0;">
                        Saludos,<br>
                        <strong style="color: #1e3a5f;">{settings.company_name}</strong>
                    </p>
                </div>
                
                <p style="text-align: center; font-size: 11px; color: #999; margin-top: 20px;">
                    Este es un mensaje automático del sistema de Intranet.
                </p>
            </div>
        </body>
        </html>
        """
        
        contenido_texto = f"""
Recordatorio de Captura de Actividades

Hola {nombre},

Te recordamos que aún no has completado la captura de tus actividades de la semana {semana}.

Por favor ingresa al sistema para registrar tus horas trabajadas:
{url_sistema}/actividades

Saludos,
{settings.company_name}
        """
        
        resultado = enviar_correo(
            destinatario=email,
            asunto=asunto,
            contenido_html=contenido_html,
            contenido_texto=contenido_texto
        )
        
        if resultado["success"]:
            enviados += 1
            detalles.append({
                "nombre": nombre, 
                "email": email, 
                "status": "enviado",
                "simulated": resultado.get("simulated", False)
            })
        else:
            fallidos += 1
            detalles.append({
                "nombre": nombre, 
                "email": email, 
                "status": "fallido",
                "error": resultado.get("message", "Error desconocido")
            })
    
    return {
        "total": len(empleados),
        "enviados": enviados,
        "fallidos": fallidos,
        "detalles": detalles
    }


def enviar_notificacion_vacaciones(
    empleado: dict,
    tipo: str,  # 'aprobada' o 'rechazada'
    fecha_inicio: str,
    fecha_fin: str,
    comentario: Optional[str] = None
) -> dict:
    """Envía notificación sobre el estado de una solicitud de vacaciones"""
    
    nombre = f"{empleado.get('nombre', '')} {empleado.get('apellidos', '')}".strip()
    email = empleado.get('email', '')
    
    if not email:
        return {"success": False, "error": "no_email", "message": "Empleado sin email"}
    
    if tipo == 'aprobada':
        asunto = "✅ Tu solicitud de vacaciones ha sido aprobada"
        estado_texto = "aprobada"
        color = "#10b981"
        icono = "✅"
    else:
        asunto = "❌ Tu solicitud de vacaciones ha sido rechazada"
        estado_texto = "rechazada"
        color = "#ef4444"
        icono = "❌"
    
    contenido_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 0; margin: 0; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0093b0 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">🏖️ Solicitud de Vacaciones</h1>
            </div>
            
            <div style="background: white; padding: 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <p style="font-size: 16px; color: #333;">Hola <strong>{nombre}</strong>,</p>
                
                <p style="font-size: 15px; color: #555; line-height: 1.6;">
                    Tu solicitud de vacaciones ha sido 
                    <strong style="color: {color};">{estado_texto}</strong> {icono}
                </p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {color};">
                    <p style="margin: 0 0 10px 0; font-size: 14px;">
                        <strong>📅 Fechas:</strong> {fecha_inicio} al {fecha_fin}
                    </p>
                    {f'<p style="margin: 0; font-size: 14px;"><strong>💬 Comentario:</strong> {comentario}</p>' if comentario else ''}
                </div>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
                
                <p style="font-size: 13px; color: #888; margin: 0;">
                    Saludos,<br>
                    <strong style="color: #1e3a5f;">{settings.company_name}</strong>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return enviar_correo(
        destinatario=email,
        asunto=asunto,
        contenido_html=contenido_html
    )


def enviar_notificacion_password(
    email: str,
    nombre: str,
    token: str,
    url_base: str = None
) -> dict:
    """Envía email para restablecer contraseña"""
    
    if url_base is None:
        url_base = settings.APP_URL
    
    link = f"{url_base}/restablecer-password?token={token}"
    
    asunto = "🔐 Restablecer contraseña - Intranet"
    
    contenido_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 0; margin: 0; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0093b0 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">🔐 Restablecer Contraseña</h1>
            </div>
            
            <div style="background: white; padding: 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <p style="font-size: 16px; color: #333;">Hola <strong>{nombre}</strong>,</p>
                
                <p style="font-size: 15px; color: #555; line-height: 1.6;">
                    Recibimos una solicitud para restablecer tu contraseña. 
                    Haz clic en el siguiente botón para crear una nueva:
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{link}" 
                       style="background: linear-gradient(135deg, #0093b0 0%, #007a94 100%); 
                              color: white; 
                              padding: 14px 32px; 
                              text-decoration: none; 
                              border-radius: 8px; 
                              font-weight: 600;
                              font-size: 15px;
                              display: inline-block;">
                        Restablecer Contraseña
                    </a>
                </div>
                
                <p style="font-size: 13px; color: #888; line-height: 1.6;">
                    Este enlace expirará en 1 hora. Si no solicitaste este cambio, 
                    puedes ignorar este mensaje.
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
                
                <p style="font-size: 13px; color: #888; margin: 0;">
                    Saludos,<br>
                    <strong style="color: #1e3a5f;">{settings.company_name}</strong>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return enviar_correo(
        destinatario=email,
        asunto=asunto,
        contenido_html=contenido_html
    )


def test_smtp_connection() -> dict:
    """Prueba la conexión SMTP sin enviar email"""
    
    logger.info("=== TEST DE CONEXIÓN SMTP ===")
    logger.info(f"Host: {settings.smtp_host}")
    logger.info(f"Port: {settings.smtp_port}")
    logger.info(f"User: {settings.smtp_user}")
    logger.info(f"SSL: {settings.smtp_use_ssl}")
    
    if not settings.smtp_user or not settings.smtp_password:
        return {
            "success": False,
            "error": "no_credentials",
            "message": "No hay credenciales SMTP configuradas en .env"
        }
    
    try:
        if settings.smtp_use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context, timeout=30) as servidor:
                logger.info("Conexión SSL establecida")
                servidor.login(settings.smtp_user, settings.smtp_password)
                logger.info("Autenticación exitosa")
                return {
                    "success": True,
                    "message": "Conexión SMTP exitosa",
                    "config": {
                        "host": settings.smtp_host,
                        "port": settings.smtp_port,
                        "user": settings.smtp_user,
                        "ssl": settings.smtp_use_ssl
                    }
                }
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as servidor:
                servidor.starttls()
                logger.info("STARTTLS establecido")
                servidor.login(settings.smtp_user, settings.smtp_password)
                logger.info("Autenticación exitosa")
                return {
                    "success": True,
                    "message": "Conexión SMTP exitosa",
                    "config": {
                        "host": settings.smtp_host,
                        "port": settings.smtp_port,
                        "user": settings.smtp_user,
                        "ssl": settings.smtp_use_ssl
                    }
                }
                
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Error en test SMTP: {error_msg}")
        return {
            "success": False,
            "error": type(e).__name__,
            "message": error_msg
        }


def enviar_notificacion_recibo_nomina(
    empleado: dict,
    periodo: str,
    mes: int,
    anio: int,
    url_sistema: str = None
) -> dict:
    """
    Envía notificación al empleado cuando se sube un nuevo recibo de nómina.
    """
    
    if url_sistema is None:
        url_sistema = settings.APP_URL
    
    nombre = f"{empleado.get('nombre', '')} {empleado.get('apellidos', '')}".strip()
    email = empleado.get('email', '')
    
    if not email:
        return {"success": False, "error": "no_email", "message": "Empleado sin email"}
    
    # Nombre del mes en español
    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    mes_nombre = meses.get(mes, f'Mes {mes}')
    
    asunto = f"💰 Nuevo recibo de nómina disponible - {periodo} {mes_nombre} {anio}"
    
    contenido_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 0; margin: 0; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">💰 Recibo de Nómina</h1>
            </div>
            
            <div style="background: white; padding: 30px; border-radius: 0 0 12px 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <p style="font-size: 16px; color: #333;">Hola <strong>{nombre}</strong>,</p>
                
                <p style="font-size: 15px; color: #555; line-height: 1.6;">
                    Tu recibo de nómina ya está disponible para consulta y descarga.
                </p>
                
                <div style="background-color: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #10b981;">
                    <p style="margin: 0 0 8px 0; font-size: 14px;">
                        <strong>📅 Período:</strong> {periodo}
                    </p>
                    <p style="margin: 0; font-size: 14px;">
                        <strong>🗓️ Mes:</strong> {mes_nombre} {anio}
                    </p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{url_sistema}/mis-recibos" 
                       style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); 
                              color: white; 
                              padding: 14px 32px; 
                              text-decoration: none; 
                              border-radius: 8px; 
                              font-weight: 600;
                              font-size: 15px;
                              display: inline-block;">
                        Ver Mis Recibos
                    </a>
                </div>
                
                <p style="font-size: 13px; color: #888; line-height: 1.6;">
                    Puedes acceder a todos tus recibos de nómina desde la sección 
                    "Mis Recibos" en el sistema.
                </p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
                
                <p style="font-size: 13px; color: #888; margin: 0;">
                    Saludos,<br>
                    <strong style="color: #059669;">{settings.company_name}</strong>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return enviar_correo(
        destinatario=email,
        asunto=asunto,
        contenido_html=contenido_html
    )


def enviar_notificacion_vacaciones(
    empleado: dict,
    vacacion: dict,
    aprobada: bool = True
) -> dict:
    """
    Envía notificación al empleado cuando su solicitud de vacaciones
    es aprobada o rechazada.
    """
    nombre = empleado.get('nombre', '')
    apellidos = empleado.get('apellidos', '')
    email = empleado.get('email', '')
    
    if not email:
        return {"success": False, "message": "Empleado sin email"}
    
    nombre_completo = f"{nombre} {apellidos}".strip()
    
    # Datos de la solicitud
    fecha_inicio = vacacion.get('fecha_inicio', '')
    fecha_fin = vacacion.get('fecha_fin', '')
    dias_solicitados = vacacion.get('dias_solicitados', 0)
    dias_especificos = vacacion.get('dias_especificos', [])
    comentario = vacacion.get('comentario_admin', '')
    
    # Determinar si mostrar días específicos o rango
    if dias_especificos and len(dias_especificos) > 0:
        dias_ordenados = sorted(dias_especificos)
        fechas_html = "<br>".join([f"📅 {d}" for d in dias_ordenados])
    else:
        fechas_html = f"📅 Del {fecha_inicio} al {fecha_fin}"
    
    if aprobada:
        asunto = f"✅ Vacaciones Aprobadas - {dias_solicitados} días"
        estado_color = "#10b981"
        estado_bg = "#d1fae5"
        estado_texto = "APROBADA"
        estado_icono = "✅"
        mensaje_principal = "¡Tu solicitud de vacaciones ha sido aprobada!"
        mensaje_secundario = "Ya puedes disfrutar de tus días de descanso en las fechas solicitadas."
    else:
        asunto = f"❌ Vacaciones Rechazadas"
        estado_color = "#ef4444"
        estado_bg = "#fee2e2"
        estado_texto = "RECHAZADA"
        estado_icono = "❌"
        mensaje_principal = "Tu solicitud de vacaciones no fue aprobada"
        mensaje_secundario = "Por favor revisa los comentarios y contacta a Recursos Humanos si tienes dudas."
    
    # Sección de comentario si existe
    comentario_html = ""
    if comentario:
        comentario_html = f"""
        <div style="background: #f8fafc; border-left: 4px solid {estado_color}; padding: 12px 16px; margin: 20px 0; border-radius: 0 8px 8px 0;">
            <p style="margin: 0; font-size: 12px; color: #64748b; font-weight: 600;">COMENTARIO DE ADMINISTRACIÓN:</p>
            <p style="margin: 8px 0 0 0; color: #334155;">{comentario}</p>
        </div>
        """
    
    contenido_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">{estado_icono} Solicitud de Vacaciones</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">{settings.company_name}</p>
                </div>
                
                <!-- Content -->
                <div style="padding: 30px;">
                    <p style="font-size: 16px; color: #333; margin-bottom: 5px;">Hola <strong>{nombre}</strong>,</p>
                    <p style="font-size: 15px; color: #555; line-height: 1.6;">{mensaje_principal}</p>
                    
                    <!-- Estado Badge -->
                    <div style="text-align: center; margin: 25px 0;">
                        <span style="display: inline-block; background: {estado_bg}; color: {estado_color}; padding: 12px 30px; border-radius: 25px; font-weight: 700; font-size: 16px;">
                            {estado_icono} {estado_texto}
                        </span>
                    </div>
                    
                    <!-- Detalle de la solicitud -->
                    <div style="background: #f8fafc; border-radius: 10px; padding: 20px; margin: 20px 0;">
                        <h3 style="margin: 0 0 15px 0; font-size: 14px; color: #64748b; text-transform: uppercase;">Detalle de la Solicitud</h3>
                        
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; color: #64748b; font-size: 13px; width: 40%;">Días solicitados:</td>
                                <td style="padding: 8px 0; color: #1e293b; font-weight: 600; font-size: 14px;">{dias_solicitados} días</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #64748b; font-size: 13px; vertical-align: top;">Fechas:</td>
                                <td style="padding: 8px 0; color: #1e293b; font-size: 14px;">{fechas_html}</td>
                            </tr>
                        </table>
                    </div>
                    
                    {comentario_html}
                    
                    <p style="font-size: 13px; color: #888; line-height: 1.6;">{mensaje_secundario}</p>
                    
                    <!-- Botón -->
                    <div style="text-align: center; margin: 25px 0;">
                        <a href="{settings.app_url}/vacaciones" 
                           style="background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
                                  color: white;
                                  padding: 14px 35px;
                                  text-decoration: none;
                                  border-radius: 8px;
                                  font-weight: 600;
                                  font-size: 15px;
                                  display: inline-block;">
                            Ver Mis Vacaciones
                        </a>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
                    
                    <p style="font-size: 13px; color: #888; margin: 0;">
                        Saludos,<br>
                        <strong style="color: #0284c7;">{settings.company_name}</strong>
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return enviar_correo(
        destinatario=email,
        asunto=asunto,
        contenido_html=contenido_html
    )
