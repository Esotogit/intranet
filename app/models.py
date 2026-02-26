from pydantic import BaseModel, EmailStr, field_serializer
from typing import Optional, Union
from datetime import date, time, datetime
from decimal import Decimal
from enum import Enum


# ===========================================
# ENUMS
# ===========================================

class EstatusVacaciones(str, Enum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


class DiaSemana(str, Enum):
    LUNES = "L"
    MARTES = "M"
    MIERCOLES = "X"
    JUEVES = "J"
    VIERNES = "V"
    SABADO = "S"
    DOMINGO = "D"


class TipoNotificacion(str, Enum):
    RECORDATORIO_ACTIVIDAD = "recordatorio_actividad"
    VACACIONES_APROBADA = "vacaciones_aprobada"
    VACACIONES_RECHAZADA = "vacaciones_rechazada"
    VACACIONES_PENDIENTE = "vacaciones_pendiente"


# ===========================================
# CATÁLOGOS
# ===========================================

class PuestoBase(BaseModel):
    nombre: str
    dias_vacaciones_anuales: int = 12


class Puesto(PuestoBase):
    id: int
    activo: bool = True

    class Config:
        from_attributes = True


class SupervisorBase(BaseModel):
    nombre: str


class Supervisor(SupervisorBase):
    id: int
    activo: bool = True

    class Config:
        from_attributes = True


class UbicacionBase(BaseModel):
    codigo: str
    nombre: str


class Ubicacion(UbicacionBase):
    id: int
    activo: bool = True

    class Config:
        from_attributes = True


class ProyectoBase(BaseModel):
    nombre: str


class Proyecto(ProyectoBase):
    id: int
    activo: bool = True

    class Config:
        from_attributes = True


# ===========================================
# EMPLEADOS
# ===========================================

class EmpleadoBase(BaseModel):
    email: EmailStr
    nombre: str
    apellidos: str
    numero_empleado: Optional[str] = None
    puesto_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    proyecto_id: Optional[int] = None
    fecha_ingreso: Optional[str] = None  # Cambiado a string para compatibilidad JSON
    dias_vacaciones: float = 0  # Cambiado de Decimal a float
    rol: str = 'usuario'  # 'admin', 'inventario', 'usuario'
    es_admin: bool = False
    # Nuevos campos
    correo_personal: Optional[str] = None
    telefono_personal: Optional[str] = None
    rfc: Optional[str] = None
    nss: Optional[str] = None
    curp: Optional[str] = None
    fecha_baja: Optional[str] = None


class EmpleadoCreate(EmpleadoBase):
    password: str


class EmpleadoUpdate(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    numero_empleado: Optional[str] = None
    puesto_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    proyecto_id: Optional[int] = None
    dias_vacaciones: Optional[float] = None
    rol: Optional[str] = None
    es_admin: Optional[bool] = None
    activo: Optional[bool] = None
    # Nuevos campos
    correo_personal: Optional[str] = None
    telefono_personal: Optional[str] = None
    rfc: Optional[str] = None
    nss: Optional[str] = None
    curp: Optional[str] = None
    fecha_baja: Optional[str] = None


class Empleado(BaseModel):
    id: str
    email: str
    nombre: str
    apellidos: str
    numero_empleado: Optional[str] = None
    puesto_id: Optional[int] = None
    supervisor_id: Optional[int] = None
    proyecto_id: Optional[int] = None
    fecha_ingreso: Optional[str] = None
    dias_vacaciones: float = 0
    rol: str = 'usuario'
    es_admin: bool = False
    activo: bool = True
    # Campos adicionales
    correo_personal: Optional[str] = None
    telefono_personal: Optional[str] = None
    rfc: Optional[str] = None
    nss: Optional[str] = None
    curp: Optional[str] = None
    fecha_baja: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class EmpleadoCompleto(BaseModel):
    """Vista completa con datos de catálogos"""
    id: str
    email: str
    nombre: str
    apellidos: str
    nombre_completo: str
    numero_empleado: Optional[str] = None
    puesto: Optional[str] = None
    supervisor: Optional[str] = None
    proyecto: Optional[str] = None
    fecha_ingreso: Optional[str] = None
    dias_vacaciones: float = 0
    rol: str = 'usuario'
    es_admin: bool
    activo: bool
    # Campos adicionales
    correo_personal: Optional[str] = None
    telefono_personal: Optional[str] = None
    rfc: Optional[str] = None
    nss: Optional[str] = None
    curp: Optional[str] = None
    fecha_baja: Optional[str] = None

    class Config:
        from_attributes = True


# ===========================================
# VACACIONES
# ===========================================

class VacacionesBase(BaseModel):
    fecha_inicio: date
    fecha_fin: date
    dias_solicitados: Decimal
    motivo: Optional[str] = None


class VacacionesCreate(VacacionesBase):
    empleado_id: Optional[str] = None  # Se asigna automáticamente del usuario autenticado
    dias_especificos: Optional[list[str]] = None  # Lista de fechas específicas seleccionadas
    tipo_solicitud: str = "usar_dias"  # usar_dias, prima_vacacional, paternidad


class VacacionesUpdate(BaseModel):
    estatus: EstatusVacaciones
    comentario_admin: Optional[str] = None


class Vacaciones(VacacionesBase):
    id: str
    empleado_id: str
    estatus: EstatusVacaciones = EstatusVacaciones.PENDIENTE
    aprobado_por: Optional[str] = None
    comentario_admin: Optional[str] = None
    dias_especificos: Optional[list[str]] = None  # Lista de fechas específicas
    tipo_solicitud: str = "usar_dias"  # usar_dias, prima_vacacional, paternidad
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# ACTIVIDADES
# ===========================================

class ActividadBase(BaseModel):
    fecha: date
    dia_semana: DiaSemana
    hora_entrada: Optional[time] = None
    hora_salida: Optional[time] = None
    descripcion: Optional[str] = None
    ubicacion_id: Optional[int] = None


class ActividadCreate(ActividadBase):
    empleado_id: str


class ActividadUpdate(BaseModel):
    hora_entrada: Optional[time] = None
    hora_salida: Optional[time] = None
    descripcion: Optional[str] = None
    ubicacion_id: Optional[int] = None


class Actividad(ActividadBase):
    id: str
    empleado_id: str
    horas_trabajadas: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class ActividadSemanalCreate(BaseModel):
    """Para crear/actualizar toda la semana de una vez"""
    semana_inicio: date  # Lunes de la semana
    actividades: list[ActividadBase]


# ===========================================
# REPORTES
# ===========================================

class ResumenSemanal(BaseModel):
    empleado_id: str
    nombre_completo: str
    proyecto: Optional[str]
    semana_inicio: date
    semana_fin: date
    total_horas: Decimal
    dias_trabajados: int


class ResumenMensual(BaseModel):
    empleado_id: str
    nombre_completo: str
    proyecto: Optional[str]
    supervisor: Optional[str]
    anio: int
    mes: int
    mes_nombre: str
    total_horas: Decimal
    dias_trabajados: int


# ===========================================
# AUTENTICACIÓN
# ===========================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    es_admin: bool = False
    rol: str = 'usuario'  # 'admin', 'inventario', 'usuario'
    tiene_puesto: bool = True  # Si tiene puesto asignado (es empleado regular)


# ===========================================
# INVENTARIO / EQUIPOS
# ===========================================

class TipoEquipo(str, Enum):
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    MONITOR = "monitor"
    TECLADO = "teclado"
    MOUSE = "mouse"
    HEADSET = "headset"
    TELEFONO = "telefono"
    IMPRESORA = "impresora"
    OTRO = "otro"


class EstadoEquipo(str, Enum):
    DISPONIBLE = "disponible"
    ASIGNADO = "asignado"
    EN_REPARACION = "en_reparacion"
    BAJA = "baja"


class EquipoBase(BaseModel):
    tipo: TipoEquipo
    marca: Optional[str] = None
    modelo: Optional[str] = None
    numero_serie: Optional[str] = None
    numero_activo: Optional[str] = None
    especificaciones: Optional[str] = None
    fecha_compra: Optional[date] = None
    proveedor: Optional[str] = None
    costo: Optional[Decimal] = None
    notas: Optional[str] = None


class EquipoCreate(EquipoBase):
    estado: Optional[EstadoEquipo] = EstadoEquipo.DISPONIBLE
    empleado_id: Optional[str] = None


class EquipoUpdate(BaseModel):
    tipo: Optional[TipoEquipo] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    numero_serie: Optional[str] = None
    numero_activo: Optional[str] = None
    especificaciones: Optional[str] = None
    estado: Optional[EstadoEquipo] = None
    fecha_compra: Optional[date] = None
    proveedor: Optional[str] = None
    costo: Optional[Decimal] = None
    notas: Optional[str] = None


class Equipo(EquipoBase):
    id: str
    estado: EstadoEquipo = EstadoEquipo.DISPONIBLE
    empleado_id: Optional[str] = None
    fecha_asignacion: Optional[date] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EquipoCompleto(Equipo):
    """Equipo con datos del empleado asignado"""
    empleado_nombre: Optional[str] = None


class AsignacionEquipo(BaseModel):
    empleado_id: str
    fecha_asignacion: Optional[date] = None
    notas: Optional[str] = None


class HistorialAsignacion(BaseModel):
    id: str
    equipo_id: str
    empleado_id: str
    empleado_nombre: str
    fecha_asignacion: date
    fecha_devolucion: Optional[date] = None
    notas: Optional[str] = None
