from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid

from app.database import supabase, get_admin_client
from app.models import TokenData
from app.auth import get_current_user, get_current_admin
from app.services.email_service import enviar_notificacion_recibo_nomina

router = APIRouter(prefix="/api/recibos", tags=["Recibos de Nómina"])


class ReciboNomina(BaseModel):
    id: int
    empleado_id: str
    empleado_nombre: Optional[str] = None
    empleado_email: Optional[str] = None
    periodo: str
    mes: int
    anio: int
    archivo_url: str
    archivo_nombre: str
    fecha_subida: Optional[datetime] = None
    notas: Optional[str] = None
    mes_nombre: Optional[str] = None


class ReciboCreate(BaseModel):
    empleado_id: str
    periodo: str
    mes: int
    anio: int
    notas: Optional[str] = None


@router.get("/mis-recibos", response_model=List[ReciboNomina])
async def obtener_mis_recibos(
    anio: Optional[int] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """Obtener recibos del empleado actual"""
    
    # Usar admin_client para bypasear RLS y filtrar manualmente por empleado
    admin_client = get_admin_client()
    
    query = admin_client.table("v_recibos_nomina").select("*").eq("empleado_id", current_user.user_id)
    
    if anio:
        query = query.eq("anio", anio)
    
    result = query.order("anio", desc=True).order("mes", desc=True).order("periodo", desc=True).execute()
    
    return result.data


@router.get("/", response_model=List[ReciboNomina])
async def listar_recibos(
    empleado_id: Optional[str] = None,
    anio: Optional[int] = None,
    mes: Optional[int] = None,
    current_user: TokenData = Depends(get_current_admin)
):
    """Listar todos los recibos (solo admin)"""
    
    query = supabase.table("v_recibos_nomina").select("*")
    
    if empleado_id:
        query = query.eq("empleado_id", empleado_id)
    if anio:
        query = query.eq("anio", anio)
    if mes:
        query = query.eq("mes", mes)
    
    result = query.order("anio", desc=True).order("mes", desc=True).order("periodo", desc=True).execute()
    
    return result.data


@router.post("/subir")
async def subir_recibo(
    archivo: UploadFile = File(...),
    empleado_id: str = Form(...),
    periodo: str = Form(...),
    mes: int = Form(...),
    anio: int = Form(...),
    notas: Optional[str] = Form(None),
    current_user: TokenData = Depends(get_current_admin)
):
    """Subir un recibo de nómina (solo admin)"""
    
    # Validar que sea PDF
    if not archivo.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten archivos PDF"
        )
    
    # Validar período
    if periodo not in ['1ra Quincena', '2da Quincena']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El período debe ser '1ra Quincena' o '2da Quincena'"
        )
    
    # Validar mes
    if mes < 1 or mes > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El mes debe estar entre 1 y 12"
        )
    
    # Verificar que el empleado existe
    emp_result = supabase.table("empleados").select("id, nombre, apellidos, email").eq("id", empleado_id).execute()
    if not emp_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    
    empleado = emp_result.data[0]
    
    # Verificar si ya existe un recibo para este período
    existing = supabase.table("recibos_nomina").select("id").eq(
        "empleado_id", empleado_id
    ).eq("periodo", periodo).eq("mes", mes).eq("anio", anio).execute()
    
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un recibo para {empleado['nombre']} {empleado['apellidos']} en {periodo} de {mes}/{anio}"
        )
    
    try:
        # Leer contenido del archivo
        contenido = await archivo.read()
        
        # Generar nombre único para el archivo
        periodo_limpio = periodo.replace(' ', '_').replace('ª', 'a')
        nombre_archivo = f"{empleado_id}/{anio}/{mes:02d}_{periodo_limpio}.pdf"
        
        # Subir a Supabase Storage
        admin_client = get_admin_client()
        
        # Intentar subir el archivo
        storage_response = admin_client.storage.from_("recibos").upload(
            nombre_archivo,
            contenido,
            {"content-type": "application/pdf"}
        )
        
        # Obtener URL pública (o firmada si el bucket es privado)
        archivo_url = admin_client.storage.from_("recibos").get_public_url(nombre_archivo)
        
        # Guardar registro en la base de datos
        recibo_data = {
            "empleado_id": empleado_id,
            "periodo": periodo,
            "mes": mes,
            "anio": anio,
            "archivo_url": archivo_url,
            "archivo_nombre": archivo.filename,
            "subido_por": current_user.user_id,
            "notas": notas
        }
        
        result = supabase.table("recibos_nomina").insert(recibo_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al guardar el registro del recibo"
            )
        
        # Enviar notificación por correo al empleado
        try:
            email_result = enviar_notificacion_recibo_nomina(
                empleado=empleado,
                periodo=periodo,
                mes=mes,
                anio=anio
            )
            print(f"[EMAIL] Notificación de recibo: {email_result}")
        except Exception as email_error:
            print(f"[WARNING] No se pudo enviar notificación de recibo: {str(email_error)}")
        
        return {
            "message": "Recibo subido exitosamente",
            "recibo": result.data[0]
        }
        
    except Exception as e:
        print(f"[ERROR] Subir recibo: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir el recibo: {str(e)}"
        )


@router.delete("/{recibo_id}")
async def eliminar_recibo(
    recibo_id: int,
    current_user: TokenData = Depends(get_current_admin)
):
    """Eliminar un recibo (solo admin)"""
    
    # Obtener el recibo para saber la URL del archivo
    recibo = supabase.table("recibos_nomina").select("*").eq("id", recibo_id).execute()
    
    if not recibo.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recibo no encontrado"
        )
    
    recibo_data = recibo.data[0]
    
    try:
        # Eliminar archivo de Storage
        admin_client = get_admin_client()
        periodo_limpio = recibo_data['periodo'].replace(' ', '_').replace('ª', 'a')
        nombre_archivo = f"{recibo_data['empleado_id']}/{recibo_data['anio']}/{recibo_data['mes']:02d}_{periodo_limpio}.pdf"
        
        admin_client.storage.from_("recibos").remove([nombre_archivo])
    except Exception as e:
        print(f"[WARNING] No se pudo eliminar archivo de storage: {str(e)}")
    
    # Eliminar registro de la base de datos
    result = supabase.table("recibos_nomina").delete().eq("id", recibo_id).execute()
    
    return {"message": "Recibo eliminado correctamente"}


@router.get("/descargar/{recibo_id}")
async def descargar_recibo(
    recibo_id: int,
    current_user: TokenData = Depends(get_current_user)
):
    """Obtener URL de descarga de un recibo"""
    
    # Usar admin_client para bypasear RLS y verificar permisos manualmente
    admin_client = get_admin_client()
    
    # Verificar que el recibo existe
    recibo = admin_client.table("recibos_nomina").select("*").eq("id", recibo_id).execute()
    
    if not recibo.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recibo no encontrado"
        )
    
    recibo_data = recibo.data[0]
    
    # Verificar permisos: admin o dueño del recibo
    if not current_user.es_admin and recibo_data['empleado_id'] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para descargar este recibo"
        )
    
    # Generar URL firmada para descarga (válida por 1 hora)
    periodo_limpio = recibo_data['periodo'].replace(' ', '_').replace('ª', 'a')
    nombre_archivo = f"{recibo_data['empleado_id']}/{recibo_data['anio']}/{recibo_data['mes']:02d}_{periodo_limpio}.pdf"
    
    try:
        signed_url = admin_client.storage.from_("recibos").create_signed_url(nombre_archivo, 3600)
        return {"url": signed_url['signedURL'], "nombre": recibo_data['archivo_nombre']}
    except Exception as e:
        print(f"[ERROR] Generar URL firmada: {str(e)}")
        # Si falla la URL firmada, devolver la URL pública
        return {"url": recibo_data['archivo_url'], "nombre": recibo_data['archivo_nombre']}


@router.get("/estadisticas")
async def estadisticas_recibos(
    current_user: TokenData = Depends(get_current_admin)
):
    """Obtener estadísticas de recibos (solo admin)"""
    
    # Total de recibos
    total = supabase.table("recibos_nomina").select("id", count="exact").execute()
    
    # Recibos por año actual
    anio_actual = datetime.now().year
    del_anio = supabase.table("recibos_nomina").select("id", count="exact").eq("anio", anio_actual).execute()
    
    # Empleados con recibos este mes
    mes_actual = datetime.now().month
    del_mes = supabase.table("recibos_nomina").select("empleado_id", count="exact").eq(
        "anio", anio_actual
    ).eq("mes", mes_actual).execute()
    
    return {
        "total_recibos": total.count or 0,
        "recibos_anio_actual": del_anio.count or 0,
        "recibos_mes_actual": del_mes.count or 0
    }


@router.post("/subir-masivo")
async def subir_recibos_masivo(
    archivos: List[UploadFile] = File(...),
    current_user: TokenData = Depends(get_current_admin)
):
    """
    Subir múltiples recibos de nómina detectando automáticamente el empleado.
    
    Formato del nombre del archivo: RE_3107_Quincenal_2026_1_356_753.pdf
    - RE: Fijo
    - 3107: Fijo
    - Quincenal: Fijo
    - 2026: Año
    - 1: Número de quincena (1-24)
    - 356: Número de empleado
    - 753: Otros dígitos (ignorados)
    """
    
    resultados = {
        "exitosos": [],
        "errores": [],
        "total": len(archivos)
    }
    
    # Obtener todos los empleados con su numero_empleado
    empleados_result = supabase.table("empleados").select("id, nombre, apellidos, email, numero_empleado").eq("activo", True).execute()
    
    # Crear diccionario para búsqueda rápida por numero_empleado
    empleados_por_numero = {}
    for emp in empleados_result.data:
        if emp.get('numero_empleado'):
            empleados_por_numero[emp['numero_empleado'].strip()] = emp
    
    admin_client = get_admin_client()
    
    for archivo in archivos:
        nombre_archivo = archivo.filename
        
        try:
            # Validar que sea PDF
            if not nombre_archivo.lower().endswith('.pdf'):
                resultados["errores"].append({
                    "archivo": nombre_archivo,
                    "error": "No es un archivo PDF"
                })
                continue
            
            # Parsear el nombre del archivo
            # RE_3107_Quincenal_2026_1_356_753.pdf
            nombre_sin_extension = nombre_archivo.rsplit('.', 1)[0]
            partes = nombre_sin_extension.split('_')
            
            if len(partes) < 6:
                resultados["errores"].append({
                    "archivo": nombre_archivo,
                    "error": "Formato de nombre inválido. Se esperan al menos 6 partes separadas por '_'"
                })
                continue
            
            # Extraer datos del nombre
            anio = int(partes[3])  # Posición 4: año
            numero_quincena = int(partes[4])  # Posición 5: número de quincena (1-24)
            numero_empleado = partes[5]  # Posición 6: número de empleado
            
            # Calcular mes y período a partir del número de quincena
            # Quincena 1 = 1ra de Enero, Quincena 2 = 2da de Enero
            # Quincena 3 = 1ra de Febrero, etc.
            mes = ((numero_quincena - 1) // 2) + 1
            es_primera_quincena = (numero_quincena % 2) == 1
            periodo = "1ra Quincena" if es_primera_quincena else "2da Quincena"
            
            # Validar mes
            if mes < 1 or mes > 12:
                resultados["errores"].append({
                    "archivo": nombre_archivo,
                    "error": f"Número de quincena inválido: {numero_quincena}. Debe estar entre 1 y 24"
                })
                continue
            
            # Buscar empleado por número
            empleado = empleados_por_numero.get(numero_empleado)
            
            if not empleado:
                resultados["errores"].append({
                    "archivo": nombre_archivo,
                    "error": f"No se encontró empleado con número: {numero_empleado}"
                })
                continue
            
            empleado_id = empleado['id']
            
            # Verificar si ya existe un recibo para este período
            existing = admin_client.table("recibos_nomina").select("id").eq(
                "empleado_id", empleado_id
            ).eq("periodo", periodo).eq("mes", mes).eq("anio", anio).execute()
            
            if existing.data:
                resultados["errores"].append({
                    "archivo": nombre_archivo,
                    "error": f"Ya existe recibo para {empleado['nombre']} {empleado['apellidos']} - {periodo} {mes}/{anio}"
                })
                continue
            
            # Leer contenido del archivo
            contenido = await archivo.read()
            
            # Generar nombre único para Storage
            periodo_limpio = periodo.replace(' ', '_').replace('ª', 'a')
            storage_path = f"{empleado_id}/{anio}/{mes:02d}_{periodo_limpio}.pdf"
            
            # Subir a Supabase Storage (intentar eliminar si existe)
            try:
                admin_client.storage.from_("recibos").remove([storage_path])
            except:
                pass  # Si no existe, no pasa nada
            
            storage_response = admin_client.storage.from_("recibos").upload(
                storage_path,
                contenido,
                {"content-type": "application/pdf"}
            )
            
            # Obtener URL
            archivo_url = admin_client.storage.from_("recibos").get_public_url(storage_path)
            
            # Guardar registro en la base de datos (usar admin_client para bypass RLS)
            recibo_data = {
                "empleado_id": empleado_id,
                "periodo": periodo,
                "mes": mes,
                "anio": anio,
                "archivo_url": archivo_url,
                "archivo_nombre": nombre_archivo,
                "subido_por": current_user.user_id,
                "notas": f"Carga masiva - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
            
            result = admin_client.table("recibos_nomina").insert(recibo_data).execute()
            
            if result.data:
                resultados["exitosos"].append({
                    "archivo": nombre_archivo,
                    "empleado": f"{empleado['nombre']} {empleado['apellidos']}",
                    "numero_empleado": numero_empleado,
                    "periodo": f"{periodo} - {mes}/{anio}"
                })
                
                # Enviar notificación por correo (sin bloquear si falla)
                try:
                    enviar_notificacion_recibo_nomina(
                        empleado=empleado,
                        periodo=periodo,
                        mes=mes,
                        anio=anio
                    )
                except Exception as email_error:
                    print(f"[WARNING] No se pudo enviar notificación a {empleado['email']}: {str(email_error)}")
            else:
                resultados["errores"].append({
                    "archivo": nombre_archivo,
                    "error": "Error al guardar en base de datos"
                })
                
        except ValueError as ve:
            resultados["errores"].append({
                "archivo": nombre_archivo,
                "error": f"Error al parsear nombre: {str(ve)}"
            })
        except Exception as e:
            resultados["errores"].append({
                "archivo": nombre_archivo,
                "error": str(e)
            })
    
    return resultados
