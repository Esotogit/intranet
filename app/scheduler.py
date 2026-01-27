from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date, timedelta

from app.database import supabase, get_admin_client
from app.services.email_service import enviar_recordatorio_actividades

scheduler = AsyncIOScheduler()


async def tarea_recordatorio_semanal():
    """
    Envía recordatorio a empleados que no han capturado actividades
    Se ejecuta los viernes a las 10:00 AM
    """
    print("[SCHEDULER] Ejecutando tarea de recordatorio semanal...")
    
    try:
        # Obtener empleados sin captura
        result = supabase.table("v_empleados_sin_captura").select("*").execute()
        
        if not result.data:
            print("[SCHEDULER] Todos los empleados han capturado sus actividades")
            return
        
        # Calcular semana actual
        hoy = date.today()
        lunes = hoy - timedelta(days=hoy.weekday())
        viernes = lunes + timedelta(days=4)
        semana = f"{lunes.strftime('%d/%m')} al {viernes.strftime('%d/%m/%Y')}"
        
        # Enviar recordatorios
        enviados = await enviar_recordatorio_actividades(
            empleados=result.data,
            semana=semana
        )
        
        print(f"[SCHEDULER] Se enviaron {enviados} recordatorios")
        
        # Registrar notificaciones en la base de datos
        admin_client = get_admin_client()
        
        for empleado in result.data:
            admin_client.table("notificaciones").insert({
                "empleado_id": empleado["id"],
                "tipo": "recordatorio_actividad",
                "mensaje": f"Recordatorio enviado para semana {semana}",
                "enviado": True
            }).execute()
            
    except Exception as e:
        print(f"[SCHEDULER] Error en tarea de recordatorio: {e}")


async def tarea_reset_vacaciones_anuales():
    """
    Resetea los días de vacaciones al inicio del año
    Se ejecuta el 1 de enero a las 00:01
    """
    print("[SCHEDULER] Ejecutando reset anual de vacaciones...")
    
    try:
        admin_client = get_admin_client()
        
        # Obtener todos los empleados activos con su puesto
        result = admin_client.table("empleados").select(
            "id, puesto_id, puestos(dias_vacaciones_anuales)"
        ).eq("activo", True).execute()
        
        for empleado in result.data:
            dias_anuales = 12  # Default
            
            if empleado.get("puestos"):
                dias_anuales = empleado["puestos"].get("dias_vacaciones_anuales", 12)
            
            admin_client.table("empleados").update({
                "dias_vacaciones": dias_anuales
            }).eq("id", empleado["id"]).execute()
        
        print(f"[SCHEDULER] Se actualizaron vacaciones de {len(result.data)} empleados")
        
    except Exception as e:
        print(f"[SCHEDULER] Error en reset de vacaciones: {e}")


def iniciar_scheduler():
    """Configura e inicia las tareas programadas"""
    
    # Recordatorio semanal: Viernes a las 10:00 AM
    scheduler.add_job(
        tarea_recordatorio_semanal,
        CronTrigger(day_of_week='fri', hour=10, minute=0),
        id='recordatorio_semanal',
        name='Recordatorio de captura de actividades',
        replace_existing=True
    )
    
    # Reset anual de vacaciones: 1 de Enero a las 00:01
    scheduler.add_job(
        tarea_reset_vacaciones_anuales,
        CronTrigger(month=1, day=1, hour=0, minute=1),
        id='reset_vacaciones',
        name='Reset anual de días de vacaciones',
        replace_existing=True
    )
    
    scheduler.start()
    print("[SCHEDULER] Tareas programadas iniciadas")


def detener_scheduler():
    """Detiene las tareas programadas"""
    scheduler.shutdown()
    print("[SCHEDULER] Tareas programadas detenidas")
