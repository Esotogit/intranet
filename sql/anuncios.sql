-- =============================================
-- MÓDULO DE ANUNCIOS / AVISOS
-- =============================================

-- Tabla de anuncios
CREATE TABLE IF NOT EXISTS anuncios (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    titulo VARCHAR(150),
    descripcion TEXT,
    imagen_url TEXT NOT NULL,
    fecha_inicio DATE DEFAULT CURRENT_DATE,
    fecha_fin DATE,
    prioridad VARCHAR(20) DEFAULT 'normal' CHECK (prioridad IN ('normal', 'importante', 'urgente')),
    activo BOOLEAN DEFAULT true,
    orden INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES empleados(id),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para mejor rendimiento
CREATE INDEX IF NOT EXISTS idx_anuncios_activo ON anuncios(activo);
CREATE INDEX IF NOT EXISTS idx_anuncios_fechas ON anuncios(fecha_inicio, fecha_fin);
CREATE INDEX IF NOT EXISTS idx_anuncios_orden ON anuncios(orden);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_anuncios_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_anuncios_updated_at ON anuncios;
CREATE TRIGGER trigger_anuncios_updated_at
    BEFORE UPDATE ON anuncios
    FOR EACH ROW
    EXECUTE FUNCTION update_anuncios_updated_at();

-- Habilitar RLS
ALTER TABLE anuncios ENABLE ROW LEVEL SECURITY;

-- Políticas RLS
DROP POLICY IF EXISTS "Todos pueden ver anuncios activos" ON anuncios;
CREATE POLICY "Todos pueden ver anuncios activos" ON anuncios
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Solo admins pueden insertar anuncios" ON anuncios;
CREATE POLICY "Solo admins pueden insertar anuncios" ON anuncios
    FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Solo admins pueden actualizar anuncios" ON anuncios;
CREATE POLICY "Solo admins pueden actualizar anuncios" ON anuncios
    FOR UPDATE USING (true);

DROP POLICY IF EXISTS "Solo admins pueden eliminar anuncios" ON anuncios;
CREATE POLICY "Solo admins pueden eliminar anuncios" ON anuncios
    FOR DELETE USING (true);

-- =============================================
-- CONFIGURACIÓN DE STORAGE PARA IMÁGENES
-- =============================================
-- Ejecutar en Supabase Dashboard -> Storage:
-- 1. Crear bucket llamado "anuncios" 
-- 2. Hacerlo público (Public bucket)
-- 3. O ejecutar este SQL:

-- INSERT INTO storage.buckets (id, name, public) 
-- VALUES ('anuncios', 'anuncios', true)
-- ON CONFLICT (id) DO NOTHING;

-- Política para permitir uploads
-- CREATE POLICY "Permitir uploads de anuncios" ON storage.objects
--     FOR INSERT WITH CHECK (bucket_id = 'anuncios');

-- CREATE POLICY "Permitir lectura pública de anuncios" ON storage.objects
--     FOR SELECT USING (bucket_id = 'anuncios');

-- CREATE POLICY "Permitir eliminar anuncios" ON storage.objects
--     FOR DELETE USING (bucket_id = 'anuncios');
