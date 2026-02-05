-- =============================================
-- AGREGAR CAMPOS ADICIONALES A EMPLEADOS
-- =============================================

-- Agregar nuevas columnas
ALTER TABLE empleados ADD COLUMN IF NOT EXISTS correo_personal VARCHAR(255);
ALTER TABLE empleados ADD COLUMN IF NOT EXISTS telefono_personal VARCHAR(20);
ALTER TABLE empleados ADD COLUMN IF NOT EXISTS rfc VARCHAR(13);
ALTER TABLE empleados ADD COLUMN IF NOT EXISTS nss VARCHAR(15);
ALTER TABLE empleados ADD COLUMN IF NOT EXISTS curp VARCHAR(18);
ALTER TABLE empleados ADD COLUMN IF NOT EXISTS fecha_baja DATE;

-- Comentarios descriptivos
COMMENT ON COLUMN empleados.correo_personal IS 'Correo electrónico personal del empleado';
COMMENT ON COLUMN empleados.telefono_personal IS 'Número de teléfono personal del empleado';
COMMENT ON COLUMN empleados.rfc IS 'Registro Federal de Contribuyentes';
COMMENT ON COLUMN empleados.nss IS 'Número de Seguro Social (IMSS)';
COMMENT ON COLUMN empleados.curp IS 'Clave Única de Registro de Población';
COMMENT ON COLUMN empleados.fecha_baja IS 'Fecha de baja del empleado';

-- =============================================
-- ACTUALIZAR VISTA v_empleados_completo
-- =============================================
DROP VIEW IF EXISTS v_empleados_completo;

CREATE VIEW v_empleados_completo AS
SELECT 
    e.id,
    e.email,
    e.nombre,
    e.apellidos,
    e.nombre || ' ' || e.apellidos AS nombre_completo,
    e.numero_empleado,
    e.puesto_id,
    p.nombre AS puesto,
    e.supervisor_id,
    s.nombre AS supervisor,
    e.proyecto_id,
    pr.nombre AS proyecto,
    e.fecha_ingreso,
    e.es_admin,
    e.rol,
    e.activo,
    e.cliente,
    e.firma_url,
    e.dias_vacaciones,
    e.correo_personal,
    e.telefono_personal,
    e.rfc,
    e.nss,
    e.curp,
    e.fecha_baja,
    e.created_at,
    e.updated_at
FROM empleados e
LEFT JOIN puestos p ON e.puesto_id = p.id
LEFT JOIN supervisores s ON e.supervisor_id = s.id
LEFT JOIN proyectos pr ON e.proyecto_id = pr.id;
