"""
Script para resetear la contraseña de un usuario en Supabase Auth
Ejecutar: python reset_password.py
"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Configuración
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Necesitas la Service Role Key

if not SUPABASE_SERVICE_KEY:
    print("=" * 60)
    print("ERROR: Necesitas agregar SUPABASE_SERVICE_KEY a tu .env")
    print("=" * 60)
    print("\nPasos para obtenerla:")
    print("1. Ve a tu proyecto en Supabase Dashboard")
    print("2. Settings → API")
    print("3. Copia 'service_role' key (la secreta, NO la anon)")
    print("4. Agrégala a tu .env como:")
    print("   SUPABASE_SERVICE_KEY=tu_key_aqui")
    print("\n" + "=" * 60)
    exit(1)

# Crear cliente con service key (tiene permisos de admin)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def reset_password(email: str, new_password: str):
    """Resetea la contraseña de un usuario"""
    try:
        # Primero buscar el usuario por email
        users = supabase.auth.admin.list_users()
        
        user_id = None
        for user in users:
            if user.email == email:
                user_id = user.id
                break
        
        if not user_id:
            print(f"❌ Usuario con email {email} no encontrado en Auth")
            print("\n¿Necesitas crear el usuario? Ejecuta:")
            print(f"   python create_auth_user.py {email} {new_password}")
            return False
        
        # Actualizar contraseña
        supabase.auth.admin.update_user_by_id(
            user_id,
            {"password": new_password}
        )
        
        print(f"✅ Contraseña actualizada para {email}")
        print(f"   Nueva contraseña: {new_password}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def create_auth_user(email: str, password: str):
    """Crea un usuario en Supabase Auth si no existe"""
    try:
        result = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True  # Marcar email como verificado
        })
        print(f"✅ Usuario creado: {email}")
        return True
    except Exception as e:
        if "already been registered" in str(e):
            print(f"ℹ️ El usuario {email} ya existe, intentando resetear contraseña...")
            return reset_password(email, password)
        print(f"❌ Error creando usuario: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("   RESET DE CONTRASEÑA - Intranet IDS")
    print("=" * 60 + "\n")
    
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
    else:
        email = input("Email del usuario: ").strip()
        password = input("Nueva contraseña (mín 6 caracteres): ").strip()
    
    if len(password) < 6:
        print("❌ La contraseña debe tener al menos 6 caracteres")
        exit(1)
    
    print(f"\nReseteando contraseña para: {email}")
    print("-" * 40)
    
    # Intentar resetear, si no existe crear
    if not reset_password(email, password):
        print("\nIntentando crear usuario...")
        create_auth_user(email, password)
    
    print("\n" + "=" * 60)
    print("   Ahora intenta iniciar sesión en la intranet")
    print("=" * 60 + "\n")
