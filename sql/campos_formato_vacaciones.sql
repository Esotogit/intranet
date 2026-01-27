-- =============================================
-- AGREGAR CAMPOS PARA FORMATO DE VACACIONES
-- =============================================

-- 1. Agregar numero_empleado a la tabla empleados
ALTER TABLE empleados 
ADD COLUMN IF NOT EXISTS numero_empleado VARCHAR(50) DEFAULT NULL;

-- 2. Agregar tipo_solicitud a la tabla vacaciones
-- Valores: 'usar_dias', 'prima_vacacional', 'paternidad'
ALTER TABLE vacaciones 
ADD COLUMN IF NOT EXISTS tipo_solicitud VARCHAR(50) DEFAULT 'usar_dias';

-- 3. Actualizar la vista v_empleados_completo para incluir numero_empleado
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
    e.activo,
    e.cliente,
    e.dias_vacaciones_extra,
    COALESCE(p.dias_vacaciones, 0) + COALESCE(e.dias_vacaciones_extra, 0) AS total_dias_vacaciones,
    e.created_at,
    e.updated_at
FROM empleados e
LEFT JOIN puestos p ON e.puesto_id = p.id
LEFT JOIN supervisores s ON e.supervisor_id = s.id
LEFT JOIN proyectos pr ON e.proyecto_id = pr.id
LEFT JOIN ubicaciones u ON e.ubicacion_id = u.id;

-- Comentarios
COMMENT ON COLUMN empleados.numero_empleado IS 'Número de empleado para formatos oficiales';
COMMENT ON COLUMN vacaciones.tipo_solicitud IS 'Tipo: usar_dias, prima_vacacional, paternidad';
