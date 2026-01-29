-- =============================================
-- SISTEMA DE ROLES DE USUARIO
-- =============================================

-- 1. Agregar columna rol a empleados
-- Valores posibles: 'admin', 'inventario', 'usuario'
-- - admin: Acceso completo a todas las funciones
-- - inventario: Solo puede ver/gestionar inventarios (además de su acceso básico)
-- - usuario: Solo acceso básico (perfil, actividades, recibos, vacaciones)
ALTER TABLE empleados 
ADD COLUMN IF NOT EXISTS rol VARCHAR(20) DEFAULT 'usuario';

-- 2. Actualizar empleados existentes que son admin
UPDATE empleados 
SET rol = 'admin' 
WHERE es_admin = true AND (rol IS NULL OR rol = 'usuario');

-- 3. Actualizar vista v_empleados_completo para incluir rol
CREATE OR REPLACE VIEW v_empleados_completo AS
SELECT 
    e.id,
    e.email,
    e.nombre,
    e.apellidos,
    e.nombre || ' ' || e.apellidos AS nombre_completo,
    e.numero_empleado,
    e.puesto_id,
    p.nombre AS puesto,
    p.dias_vacaciones AS dias_vacaciones_puesto,
    e.supervisor_id,
    s.nombre AS supervisor,
    e.proyecto_id,
    pr.nombre AS proyecto,
    e.ubicacion_id,
    u.nombre AS ubicacion,
    e.fecha_ingreso,
    e.es_admin,
    e.rol,
    e.activo,
    e.cliente,
    e.firma_url,
    e.dias_vacaciones_extra,
    COALESCE(p.dias_vacaciones, 0) + COALESCE(e.dias_vacaciones_extra, 0) AS total_dias_vacaciones,
    e.created_at,
    e.updated_at
FROM empleados e
LEFT JOIN puestos p ON e.puesto_id = p.id
LEFT JOIN supervisores s ON e.supervisor_id = s.id
LEFT JOIN proyectos pr ON e.proyecto_id = pr.id
LEFT JOIN ubicaciones u ON e.ubicacion_id = u.id;

-- 4. Crear índice para búsquedas por rol
CREATE INDEX IF NOT EXISTS idx_empleados_rol ON empleados(rol);

COMMENT ON COLUMN empleados.rol IS 'Rol del usuario: admin (acceso total), inventario (gestión de inventarios), usuario (acceso básico)';
