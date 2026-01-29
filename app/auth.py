from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.models import TokenData

settings = get_settings()

# Configuración de seguridad
SECRET_KEY = settings.secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Genera el hash de una contraseña"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decodifica y valida un token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        es_admin: bool = payload.get("es_admin", False)
        rol: str = payload.get("rol", "usuario")
        tiene_puesto: bool = payload.get("tiene_puesto", True)
        
        if user_id is None:
            return None
            
        return TokenData(user_id=user_id, email=email, es_admin=es_admin, rol=rol, tiene_puesto=tiene_puesto)
    except JWTError:
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> TokenData:
    """Obtiene el usuario actual desde el token o la sesión"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = None
    
    # Intentar obtener token del header Authorization
    if credentials:
        token = credentials.credentials
    
    # Si no hay token en header, intentar desde cookie
    if not token:
        token = request.cookies.get("access_token")
    
    if not token:
        raise credentials_exception
    
    token_data = decode_token(token)
    
    if token_data is None:
        raise credentials_exception
    
    return token_data


async def get_current_admin(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """Verifica que el usuario actual sea administrador"""
    if not current_user.es_admin and current_user.rol != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    return current_user


async def get_inventario_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """Verifica que el usuario tenga acceso a inventario (admin o rol inventario)"""
    if not current_user.es_admin and current_user.rol not in ['admin', 'inventario']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para gestionar inventario"
        )
    return current_user


def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """Obtiene el usuario si está autenticado, None si no"""
    token = None
    
    if credentials:
        token = credentials.credentials
    
    if not token:
        token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    return decode_token(token)
