from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
import uuid

from app.database import supabase, get_admin_client
from app.models import (
    Empleado, 
    EmpleadoCreate, 
    EmpleadoUpdate, 
    EmpleadoCompleto,
    TokenData
)
from app.auth import get_current_user, get_current_admin, get_password_hash, get_inventario_user

router = APIRouter(prefix="/api/empleados", tags=["Empleados"])


@router.get("/me", response_model=EmpleadoCompleto)
async def get_mi_perfil(current_user: TokenData = Depends(get_current_user)):
    """Obtener perfil del usuario actual"""
    
    result = supabase.table("v_empleados_completo").select("*").eq("id", current_user.user_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    
    return result.data[0]


@router.get("/", response_model=List[EmpleadoCompleto])
async def listar_empleados(
    activo: bool = True,
    current_user: TokenData = Depends(get_inventario_user)
):
    """Listar todos los empleados (admin o inventario)"""
    
    query = supabase.table("v_empleados_completo").select("*")
    
    if activo is not None:
        query = query.eq("activo", activo)
    
    result = query.order("nombre_completo").execute()
    
    return result.data


@router.get("/{empleado_id}", response_model=EmpleadoCompleto)
async def obtener_empleado(
    empleado_id: str,
    current_user: TokenData = Depends(get_current_admin)
):
    """Obtener un empleado por ID (solo admin)"""
    
    result = supabase.table("v_empleados_completo").select("*").eq("id", empleado_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    
    return result.data[0]


@router.post("/", response_model=Empleado, status_code=status.HTTP_201_CREATED)
async def crear_empleado(
    empleado: EmpleadoCreate,
    current_user: TokenData = Depends(get_current_admin)
):
    """Crear un nuevo empleado (solo admin)"""
    
    print(f"[DEBUG] Datos recibidos: {empleado.model_dump()}")
    
    # Verificar si ya existe un empleado con ese email
    existing = supabase.table("empleados").select("id").eq("email", empleado.email).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un empleado con este correo electrónico"
        )
    
    admin_client = get_admin_client()
    auth_user_id = None
    
    # Intentar crear usuario en Supabase Auth
    try:
        auth_response = admin_client.auth.admin.create_user({
            "email": empleado.email,
            "password": empleado.password,
            "email_confirm": True
        })
        auth_user_id = auth_response.user.id
    except Exception as e:
        error_msg = str(e)
        
        # Si el usuario ya existe en Auth, intentar obtener su ID
        if "already been registered" in error_msg or "already exists" in error_msg.lower():
            try:
                # Buscar el usuario existente por email
                users_response = admin_client.auth.admin.list_users()
                for user in users_response:
                    if user.email == empleado.email:
                        auth_user_id = user.id
                        # Actualizar la contraseña del usuario existente
                        admin_client.auth.admin.update_user_by_id(
                            auth_user_id,
                            {"password": empleado.password}
                        )
                        break
                
                if not auth_user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="El correo ya está registrado pero no se pudo recuperar el usuario"
                    )
            except HTTPException:
                raise
            except Exception as inner_e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error al recuperar usuario existente: {str(inner_e)}"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al crear usuario: {error_msg}"
            )
    
    # Crear empleado en la tabla
    empleado_data = empleado.model_dump(exclude={"password"})
    empleado_data["auth_user_id"] = auth_user_id
    
    # Convertir None strings a null para campos opcionales
    for key in ["puesto_id", "supervisor_id", "proyecto_id"]:
        if empleado_data.get(key) == "" or empleado_data.get(key) == "null":
            empleado_data[key] = None
    
    try:
        result = supabase.table("empleados").insert(empleado_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear empleado en la base de datos"
            )
        
        return result.data[0]
    except Exception as e:
        # Si falla la inserción en la tabla, no eliminamos el usuario de Auth
        # porque podría ser un usuario que ya existía
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear empleado: {str(e)}"
        )


@router.patch("/{empleado_id}", response_model=Empleado)
async def actualizar_empleado(
    empleado_id: str,
    empleado: EmpleadoUpdate,
    current_user: TokenData = Depends(get_current_admin)
):
    """Actualizar un empleado (solo admin)"""
    
    # Obtener los campos que fueron enviados (incluyendo None para limpiar)
    update_data = {}
    datos_enviados = empleado.model_dump()
    
    # Lista de campos que pueden ser limpiados (establecidos a null)
    campos_limpiables = [
        'correo_personal', 'telefono_personal', 'rfc', 'nss', 'curp', 
        'fecha_baja', 'numero_empleado', 'puesto_id', 'supervisor_id', 'proyecto_id'
    ]
    
    for k, v in datos_enviados.items():
        # Incluir el campo si tiene valor O si es un campo limpiable
        if v is not None or k in campos_limpiables:
            update_data[k] = v
    
    # Remover campos que realmente no queremos actualizar (None y no fueron enviados explícitamente)
    # Para campos requeridos como nombre/apellidos, solo incluir si tienen valor
    if update_data.get('nombre') is None:
        update_data.pop('nombre', None)
    if update_data.get('apellidos') is None:
        update_data.pop('apellidos', None)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay datos para actualizar"
        )
    
    print(f"[DEBUG] Actualizando empleado {empleado_id} con: {update_data}")
    
    result = supabase.table("empleados").update(update_data).eq("id", empleado_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    
    return result.data[0]


@router.delete("/{empleado_id}")
async def desactivar_empleado(
    empleado_id: str,
    current_user: TokenData = Depends(get_current_admin)
):
    """Desactivar un empleado (solo admin)"""
    
    result = supabase.table("empleados").update({"activo": False}).eq("id", empleado_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    
    return {"message": "Empleado desactivado correctamente"}


from pydantic import BaseModel

class CambiarPasswordRequest(BaseModel):
    nueva_password: str

@router.post("/{empleado_id}/cambiar-password")
async def cambiar_password_empleado(
    empleado_id: str,
    request: CambiarPasswordRequest,
    current_user: TokenData = Depends(get_current_admin)
):
    """Cambiar contraseña de un empleado (solo admin)"""
    
    if len(request.nueva_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres"
        )
    
    # Verificar que el empleado existe
    result = supabase.table("empleados").select("id, email").eq("id", empleado_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empleado no encontrado"
        )
    
    # Usar admin client para actualizar contraseña en Auth
    admin_client = get_admin_client()
    
    try:
        # Actualizar contraseña en Supabase Auth usando el método correcto
        response = admin_client.auth.admin.update_user_by_id(
            empleado_id,
            attributes={"password": request.nueva_password}
        )
        
        if response.user:
            return {"message": "Contraseña actualizada correctamente"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se pudo actualizar la contraseña"
            )
    except Exception as e:
        print(f"[ERROR] Cambio de contraseña: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cambiar contraseña: {str(e)}"
        )


# ========================================
# FIRMA DIGITAL
# ========================================

@router.get("/mi-firma")
async def obtener_mi_firma(current_user: TokenData = Depends(get_current_user)):
    """Obtener la URL de la firma del usuario actual"""
    
    result = supabase.table("empleados").select("firma_url").eq("id", current_user.user_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    return {"firma_url": result.data[0].get("firma_url")}


@router.post("/subir-firma")
async def subir_firma(
    firma: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """Subir firma digital del empleado"""
    
    # Validar tipo de archivo
    if firma.content_type not in ["image/png", "image/jpeg"]:
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten archivos PNG o JPG"
        )
    
    # Validar tamaño (500KB)
    contents = await firma.read()
    if len(contents) > 500 * 1024:
        raise HTTPException(
            status_code=400,
            detail="El archivo es muy grande. Máximo 500KB"
        )
    
    try:
        admin_client = get_admin_client()
        
        # Generar nombre único
        extension = "png" if firma.content_type == "image/png" else "jpg"
        filename = f"firmas/{current_user.user_id}.{extension}"
        
        # Eliminar firma anterior si existe
        try:
            admin_client.storage.from_("firmas").remove([f"{current_user.user_id}.png", f"{current_user.user_id}.jpg"])
        except:
            pass
        
        # Subir nueva firma
        result = admin_client.storage.from_("firmas").upload(
            filename,
            contents,
            {"content-type": firma.content_type, "upsert": "true"}
        )
        
        # Obtener URL pública
        firma_url = admin_client.storage.from_("firmas").get_public_url(filename)
        
        # Guardar URL en la tabla empleados
        supabase.table("empleados").update({
            "firma_url": firma_url
        }).eq("id", current_user.user_id).execute()
        
        return {"message": "Firma subida correctamente", "firma_url": firma_url}
        
    except Exception as e:
        print(f"[ERROR] Subir firma: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al subir firma: {str(e)}"
        )


@router.get("/{empleado_id}/firma")
async def obtener_firma_empleado(
    empleado_id: str,
    current_user: TokenData = Depends(get_current_admin)
):
    """Obtener la URL de la firma de un empleado (solo admin)"""
    
    result = supabase.table("empleados").select("firma_url").eq("id", empleado_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    
    return {"firma_url": result.data[0].get("firma_url")}
