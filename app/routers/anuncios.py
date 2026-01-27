from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
from datetime import date
import uuid
import base64

from app.database import supabase
from app.models import TokenData
from app.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/api/anuncios", tags=["Anuncios"])


@router.get("/activos")
async def obtener_anuncios_activos(current_user: TokenData = Depends(get_current_user)):
    """Obtener anuncios activos para mostrar en el dashboard"""
    
    today = date.today().isoformat()
    
    # Obtener anuncios activos dentro del rango de fechas
    result = supabase.table("anuncios").select("*").eq("activo", True).lte("fecha_inicio", today).order("orden").order("prioridad", desc=True).execute()
    
    # Filtrar los que ya expiraron
    anuncios = []
    for anuncio in result.data:
        if anuncio.get("fecha_fin"):
            if anuncio["fecha_fin"] >= today:
                anuncios.append(anuncio)
        else:
            anuncios.append(anuncio)
    
    return anuncios


@router.get("/")
async def listar_anuncios(
    activo: Optional[bool] = None,
    current_user: TokenData = Depends(get_current_admin)
):
    """Listar todos los anuncios (admin)"""
    
    query = supabase.table("anuncios").select("*")
    
    if activo is not None:
        query = query.eq("activo", activo)
    
    result = query.order("orden").order("created_at", desc=True).execute()
    
    return result.data


@router.get("/{anuncio_id}")
async def obtener_anuncio(
    anuncio_id: str,
    current_user: TokenData = Depends(get_current_admin)
):
    """Obtener un anuncio por ID"""
    
    result = supabase.table("anuncios").select("*").eq("id", anuncio_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anuncio no encontrado"
        )
    
    return result.data[0]


@router.post("/")
async def crear_anuncio(
    titulo: Optional[str] = Form(None),
    descripcion: Optional[str] = Form(None),
    fecha_inicio: Optional[str] = Form(None),
    fecha_fin: Optional[str] = Form(None),
    prioridad: str = Form("normal"),
    imagen: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_admin)
):
    """Crear un nuevo anuncio con imagen"""
    
    # Validar tipo de archivo
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if imagen.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de archivo no permitido. Use JPG, PNG, GIF o WebP"
        )
    
    # Leer contenido del archivo
    content = await imagen.read()
    
    # Limitar tamaño (5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen no debe superar 5MB"
        )
    
    # Generar nombre único para el archivo
    extension = imagen.filename.split(".")[-1] if "." in imagen.filename else "jpg"
    filename = f"{uuid.uuid4()}.{extension}"
    
    # Subir a Supabase Storage
    try:
        storage_response = supabase.storage.from_("anuncios").upload(
            filename,
            content,
            {"content-type": imagen.content_type}
        )
        
        # Obtener URL pública
        imagen_url = supabase.storage.from_("anuncios").get_public_url(filename)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir imagen: {str(e)}"
        )
    
    # Obtener el siguiente orden
    orden_result = supabase.table("anuncios").select("orden").order("orden", desc=True).limit(1).execute()
    siguiente_orden = (orden_result.data[0]["orden"] + 1) if orden_result.data else 0
    
    # Crear registro en la base de datos
    anuncio_data = {
        "titulo": titulo,
        "descripcion": descripcion,
        "imagen_url": imagen_url,
        "fecha_inicio": fecha_inicio or date.today().isoformat(),
        "fecha_fin": fecha_fin if fecha_fin else None,
        "prioridad": prioridad,
        "orden": siguiente_orden,
        "created_by": current_user.user_id
    }
    
    result = supabase.table("anuncios").insert(anuncio_data).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear anuncio"
        )
    
    return result.data[0]


@router.post("/base64")
async def crear_anuncio_base64(
    data: dict,
    current_user: TokenData = Depends(get_current_admin)
):
    """Crear anuncio con imagen en base64 (alternativa para drag & drop)"""
    
    imagen_base64 = data.get("imagen_base64")
    if not imagen_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagen requerida"
        )
    
    # Extraer tipo y datos de la imagen base64
    if "," in imagen_base64:
        header, imagen_data = imagen_base64.split(",", 1)
        # Detectar tipo de imagen
        if "png" in header:
            extension = "png"
            content_type = "image/png"
        elif "gif" in header:
            extension = "gif"
            content_type = "image/gif"
        elif "webp" in header:
            extension = "webp"
            content_type = "image/webp"
        else:
            extension = "jpg"
            content_type = "image/jpeg"
    else:
        imagen_data = imagen_base64
        extension = "jpg"
        content_type = "image/jpeg"
    
    # Decodificar base64
    try:
        content = base64.b64decode(imagen_data)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagen base64 inválida"
        )
    
    # Limitar tamaño (5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen no debe superar 5MB"
        )
    
    # Generar nombre único
    filename = f"{uuid.uuid4()}.{extension}"
    
    # Subir a Supabase Storage
    try:
        supabase.storage.from_("anuncios").upload(
            filename,
            content,
            {"content-type": content_type}
        )
        
        imagen_url = supabase.storage.from_("anuncios").get_public_url(filename)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir imagen: {str(e)}"
        )
    
    # Obtener siguiente orden
    orden_result = supabase.table("anuncios").select("orden").order("orden", desc=True).limit(1).execute()
    siguiente_orden = (orden_result.data[0]["orden"] + 1) if orden_result.data else 0
    
    # Crear registro
    anuncio_data = {
        "titulo": data.get("titulo"),
        "descripcion": data.get("descripcion"),
        "imagen_url": imagen_url,
        "fecha_inicio": data.get("fecha_inicio") or date.today().isoformat(),
        "fecha_fin": data.get("fecha_fin") if data.get("fecha_fin") else None,
        "prioridad": data.get("prioridad", "normal"),
        "orden": siguiente_orden,
        "created_by": current_user.user_id
    }
    
    result = supabase.table("anuncios").insert(anuncio_data).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear anuncio"
        )
    
    return result.data[0]


@router.patch("/{anuncio_id}")
async def actualizar_anuncio(
    anuncio_id: str,
    data: dict,
    current_user: TokenData = Depends(get_current_admin)
):
    """Actualizar un anuncio"""
    
    # Campos permitidos para actualizar
    campos_permitidos = ["titulo", "descripcion", "fecha_inicio", "fecha_fin", "prioridad", "activo", "orden"]
    update_data = {k: v for k, v in data.items() if k in campos_permitidos}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay datos para actualizar"
        )
    
    result = supabase.table("anuncios").update(update_data).eq("id", anuncio_id).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anuncio no encontrado"
        )
    
    return result.data[0]


@router.patch("/{anuncio_id}/imagen")
async def actualizar_imagen_anuncio(
    anuncio_id: str,
    data: dict,
    current_user: TokenData = Depends(get_current_admin)
):
    """Actualizar solo la imagen de un anuncio"""
    
    imagen_base64 = data.get("imagen_base64")
    if not imagen_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Imagen requerida"
        )
    
    # Obtener anuncio actual para eliminar imagen anterior
    anuncio_result = supabase.table("anuncios").select("imagen_url").eq("id", anuncio_id).execute()
    if not anuncio_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anuncio no encontrado"
        )
    
    # Procesar nueva imagen
    if "," in imagen_base64:
        header, imagen_data = imagen_base64.split(",", 1)
        if "png" in header:
            extension, content_type = "png", "image/png"
        elif "gif" in header:
            extension, content_type = "gif", "image/gif"
        elif "webp" in header:
            extension, content_type = "webp", "image/webp"
        else:
            extension, content_type = "jpg", "image/jpeg"
    else:
        imagen_data = imagen_base64
        extension, content_type = "jpg", "image/jpeg"
    
    content = base64.b64decode(imagen_data)
    filename = f"{uuid.uuid4()}.{extension}"
    
    # Subir nueva imagen
    try:
        supabase.storage.from_("anuncios").upload(
            filename,
            content,
            {"content-type": content_type}
        )
        
        imagen_url = supabase.storage.from_("anuncios").get_public_url(filename)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir imagen: {str(e)}"
        )
    
    # Actualizar URL en la base de datos
    result = supabase.table("anuncios").update({"imagen_url": imagen_url}).eq("id", anuncio_id).execute()
    
    # Intentar eliminar imagen anterior (no crítico si falla)
    try:
        old_url = anuncio_result.data[0]["imagen_url"]
        if old_url and "anuncios/" in old_url:
            old_filename = old_url.split("anuncios/")[-1].split("?")[0]
            supabase.storage.from_("anuncios").remove([old_filename])
    except:
        pass
    
    return result.data[0]


@router.delete("/{anuncio_id}")
async def eliminar_anuncio(
    anuncio_id: str,
    current_user: TokenData = Depends(get_current_admin)
):
    """Eliminar un anuncio"""
    
    # Obtener anuncio para eliminar imagen
    anuncio_result = supabase.table("anuncios").select("imagen_url").eq("id", anuncio_id).execute()
    
    if not anuncio_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anuncio no encontrado"
        )
    
    # Eliminar de la base de datos
    supabase.table("anuncios").delete().eq("id", anuncio_id).execute()
    
    # Intentar eliminar imagen del storage
    try:
        imagen_url = anuncio_result.data[0]["imagen_url"]
        if imagen_url and "anuncios/" in imagen_url:
            filename = imagen_url.split("anuncios/")[-1].split("?")[0]
            supabase.storage.from_("anuncios").remove([filename])
    except:
        pass
    
    return {"message": "Anuncio eliminado correctamente"}


@router.post("/reordenar")
async def reordenar_anuncios(
    data: dict,
    current_user: TokenData = Depends(get_current_admin)
):
    """Reordenar anuncios (recibe lista de IDs en el nuevo orden)"""
    
    orden_ids = data.get("orden", [])
    
    for index, anuncio_id in enumerate(orden_ids):
        supabase.table("anuncios").update({"orden": index}).eq("id", anuncio_id).execute()
    
    return {"message": "Orden actualizado"}
