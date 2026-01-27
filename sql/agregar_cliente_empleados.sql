-- =============================================
-- AGREGAR CAMPO CLIENTE A EMPLEADOS
-- =============================================

-- Agregar columna cliente con valor por defecto
ALTER TABLE empleados 
ADD COLUMN IF NOT EXISTS cliente VARCHAR(255) DEFAULT 'Jugos del Valle S.A.P.I. de C.V.';

-- Actualizar todos los empleados existentes con el valor por defecto
UPDATE empleados 
SET cliente = 'Jugos del Valle S.A.P.I. de C.V.' 
WHERE cliente IS NULL;

-- Actualizar la vista v_empleados_completo para incluir el campo cliente
CREATE OR REPLACE VIEW v_empleados_completo AS
SELECT 
    e.id,
    e.email,
    e.nombre,
    e.apellidos,
    e.nombre || ' ' || e.apellidos AS nombre_completo,
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
