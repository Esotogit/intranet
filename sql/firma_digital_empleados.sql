-- =============================================
-- AGREGAR FIRMA DIGITAL A EMPLEADOS
-- =============================================

-- 1. Agregar columna firma_url a empleados
ALTER TABLE empleados 
ADD COLUMN IF NOT EXISTS firma_url TEXT DEFAULT NULL;

-- 2. Actualizar vista v_empleados_completo para incluir firma_url
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

-- 3. Crear bucket para firmas en Storage (ejecutar en Supabase Dashboard)
-- Ir a Storage -> New Bucket -> Nombre: "firmas" -> Public: true

-- 4. Política de acceso para el bucket (ejecutar en SQL Editor de Supabase)
-- Permitir a usuarios autenticados subir su propia firma:
/*
CREATE POLICY "Users can upload their own signature"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'firmas' AND (storage.foldername(name))[1] = 'firmas');

CREATE POLICY "Users can update their own signature"
ON storage.objects FOR UPDATE
TO authenticated
USING (bucket_id = 'firmas');

CREATE POLICY "Anyone can view signatures"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'firmas');

CREATE POLICY "Users can delete their own signature"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'firmas');
*/

COMMENT ON COLUMN empleados.firma_url IS 'URL de la firma digital del empleado (imagen PNG/JPG)';
