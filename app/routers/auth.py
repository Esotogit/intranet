from fastapi import APIRouter, HTTPException, status, Response, Request
from fastapi.responses import RedirectResponse
from datetime import timedelta
from pydantic import BaseModel, EmailStr

from app.database import supabase
from app.models import LoginRequest, Token
from app.auth import (
    verify_password, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_password_hash
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Autenticación"])


class RecuperarPasswordRequest(BaseModel):
    email: EmailStr


class ActualizarPasswordRequest(BaseModel):
    password: str
    access_token: str


@router.post("/login", response_model=Token)
async def login(response: Response, login_data: LoginRequest):
    """Iniciar sesión y obtener token"""
    
    # Buscar empleado por email
    result = supabase.table("empleados").select("*").eq("email", login_data.email).eq("activo", True).execute()
    
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    empleado = result.data[0]
    
    # Verificar con Supabase Auth
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": login_data.email,
            "password": login_data.password
        })
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    # Crear token propio para la aplicación
    access_token = create_access_token(
        data={
            "sub": empleado["id"],
            "email": empleado["email"],
            "es_admin": empleado["es_admin"],
            "tiene_puesto": empleado.get("puesto_id") is not None
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Guardar token en cookie httponly
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax"
    )
    
    return Token(access_token=access_token)


@router.post("/logout")
async def logout(response: Response):
    """Cerrar sesión"""
    response.delete_cookie("access_token")
    return {"message": "Sesión cerrada correctamente"}


@router.get("/logout")
async def logout_redirect(response: Response):
    """Cerrar sesión y redirigir al login"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response


@router.post("/recuperar-password")
async def recuperar_password(request: RecuperarPasswordRequest):
    """Enviar email de recuperación de contraseña"""
    
    # Verificar que el empleado existe
    result = supabase.table("empleados").select("id, email").eq("email", request.email).eq("activo", True).execute()
    
    if not result.data:
        # Por seguridad, no revelamos si el email existe o no
        return {"message": "Si el correo existe en nuestro sistema, recibirás un enlace para restablecer tu contraseña"}
    
    try:
        # Usar Supabase Auth para enviar el email de recuperación
        # El redirect_to debe ser la URL donde el usuario restablecerá su contraseña
        base_url = settings.APP_URL if hasattr(settings, 'APP_URL') else "http://localhost:8000"
        
        supabase.auth.reset_password_email(
            request.email,
            options={
                "redirect_to": f"{base_url}/restablecer-password"
            }
        )
        
        return {"message": "Se ha enviado un enlace a tu correo electrónico para restablecer tu contraseña"}
    
    except Exception as e:
        print(f"Error enviando email de recuperación: {e}")
        # Por seguridad, no revelamos el error exacto
        return {"message": "Si el correo existe en nuestro sistema, recibirás un enlace para restablecer tu contraseña"}


@router.post("/actualizar-password")
async def actualizar_password(request: ActualizarPasswordRequest):
    """Actualizar contraseña con el token de recuperación"""
    
    if not request.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token no proporcionado"
        )
    
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres"
        )
    
    try:
        # Usar el token para actualizar la contraseña en Supabase
        # Primero establecemos la sesión con el token de recuperación
        supabase.auth.set_session(request.access_token, "")
        
        # Luego actualizamos la contraseña
        supabase.auth.update_user({
            "password": request.password
        })
        
        return {"message": "Contraseña actualizada correctamente"}
    
    except Exception as e:
        print(f"Error actualizando contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo actualizar la contraseña. El enlace puede haber expirado."
        )


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


@router.post("/cambiar-password")
async def cambiar_password(request: Request, data: CambiarPasswordRequest):
    """Cambiar contraseña del usuario logueado"""
    from app.auth import get_current_user, decode_token
    
    # Obtener token de la cookie
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado"
        )
    
    # Decodificar token para obtener email
    token_data = decode_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    if len(data.password_nueva) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres"
        )
    
    try:
        # Verificar contraseña actual haciendo login
        auth_response = supabase.auth.sign_in_with_password({
            "email": token_data.email,
            "password": data.password_actual
        })
        
        # Si el login fue exitoso, actualizar contraseña
        supabase.auth.update_user({
            "password": data.password_nueva
        })
        
        return {"message": "Contraseña actualizada correctamente"}
    
    except Exception as e:
        print(f"Error cambiando contraseña: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta"
        )
