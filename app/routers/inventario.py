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
        "*, empleados(nombre, apellidos)"
    ).order("created_at", desc=True)
    
    if tipo:
        query = query.eq("tipo", tipo.value)
    if estado:
        query = query.eq("estado", estado.value)
    if empleado_id:
        query = query.eq("empleado_id", empleado_id)
    
    response = query.execute()
    
    print(f"[DEBUG] Equipos encontrados: {len(response.data)}")
    
    # Formatear respuesta con nombre del empleado
    equipos = []
    for eq in response.data:
        empleado = eq.pop("empleados", None)
        eq["empleado_nombre"] = f"{empleado['nombre']} {empleado['apellidos']}" if empleado else None
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
    
    empleado_id = equipo.data["empleado_id"]
    
    # Actualizar historial con fecha de devolución
    admin_client.table("historial_equipos").update({
        "fecha_devolucion": str(date.today()),
        "notas": notas
    }).eq("equipo_id", equipo_id).eq(
        "empleado_id", empleado_id
    ).is_("fecha_devolucion", "null").execute()
    
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
