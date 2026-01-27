-- =============================================
-- MÓDULO DE RECIBOS DE NÓMINA
-- =============================================

-- Tabla principal de recibos
CREATE TABLE IF NOT EXISTS recibos_nomina (
    id SERIAL PRIMARY KEY,
    empleado_id UUID NOT NULL REFERENCES empleados(id) ON DELETE CASCADE,
    periodo VARCHAR(20) NOT NULL, -- '1ra Quincena' o '2da Quincena'
    mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    anio INTEGER NOT NULL CHECK (anio >= 2020),
    archivo_url TEXT NOT NULL,
    archivo_nombre VARCHAR(255) NOT NULL,
    fecha_subida TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    subido_por UUID REFERENCES empleados(id),
    notas TEXT,
    UNIQUE(empleado_id, periodo, mes, anio) -- Un recibo por empleado por período
);

-- Índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_recibos_empleado ON recibos_nomina(empleado_id);
CREATE INDEX IF NOT EXISTS idx_recibos_periodo ON recibos_nomina(anio, mes, periodo);
CREATE INDEX IF NOT EXISTS idx_recibos_fecha ON recibos_nomina(fecha_subida DESC);

-- Habilitar RLS
ALTER TABLE recibos_nomina ENABLE ROW LEVEL SECURITY;

-- Políticas RLS
-- Los empleados solo ven sus propios recibos
CREATE POLICY "Empleados ven sus recibos" ON recibos_nomina
    FOR SELECT
    USING (empleado_id = auth.uid());

-- Los admins pueden ver todos los recibos
CREATE POLICY "Admins ven todos los recibos" ON recibos_nomina
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM empleados 
            WHERE id = auth.uid() AND es_admin = true
        )
    );

-- Solo admins pueden insertar
CREATE POLICY "Admins insertan recibos" ON recibos_nomina
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM empleados 
            WHERE id = auth.uid() AND es_admin = true
        )
    );

-- Solo admins pueden eliminar
CREATE POLICY "Admins eliminan recibos" ON recibos_nomina
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM empleados 
            WHERE id = auth.uid() AND es_admin = true
        )
    );

-- Vista con información del empleado
CREATE OR REPLACE VIEW v_recibos_nomina AS
SELECT 
    r.id,
    r.empleado_id,
    e.nombre || ' ' || e.apellidos AS empleado_nombre,
    e.email AS empleado_email,
    r.periodo,
    r.mes,
    r.anio,
    r.archivo_url,
    r.archivo_nombre,
    r.fecha_subida,
    r.notas,
    CASE r.mes
        WHEN 1 THEN 'Enero'
        WHEN 2 THEN 'Febrero'
        WHEN 3 THEN 'Marzo'
        WHEN 4 THEN 'Abril'
        WHEN 5 THEN 'Mayo'
        WHEN 6 THEN 'Junio'
        WHEN 7 THEN 'Julio'
        WHEN 8 THEN 'Agosto'
        WHEN 9 THEN 'Septiembre'
        WHEN 10 THEN 'Octubre'
        WHEN 11 THEN 'Noviembre'
        WHEN 12 THEN 'Diciembre'
    END AS mes_nombre
FROM recibos_nomina r
JOIN empleados e ON r.empleado_id = e.id;

-- Configurar Storage bucket para recibos (ejecutar en Supabase Dashboard)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('recibos', 'recibos', false);

-- Política de storage para recibos
-- CREATE POLICY "Admins suben recibos" ON storage.objects FOR INSERT 
-- WITH CHECK (bucket_id = 'recibos' AND EXISTS (SELECT 1 FROM empleados WHERE id = auth.uid() AND es_admin = true));

-- CREATE POLICY "Usuarios descargan sus recibos" ON storage.objects FOR SELECT 
-- USING (bucket_id = 'recibos' AND (
--     EXISTS (SELECT 1 FROM empleados WHERE id = auth.uid() AND es_admin = true) OR
--     (storage.foldername(name))[1] = auth.uid()::text
-- ));
