-- =============================================
-- CATÁLOGO DE MARCAS PARA INVENTARIO
-- =============================================

-- 1. Crear tabla de marcas
CREATE TABLE IF NOT EXISTS marcas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    activo BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Agregar columna marca_id a equipos (tabla de inventario)
ALTER TABLE equipos 
ADD COLUMN IF NOT EXISTS marca_id UUID REFERENCES marcas(id);

-- 3. Insertar algunas marcas comunes
INSERT INTO marcas (nombre) VALUES 
    ('Dell'),
    ('HP'),
    ('Lenovo'),
    ('Apple'),
    ('Asus'),
    ('Acer'),
    ('Samsung'),
    ('LG'),
    ('Microsoft'),
    ('Logitech'),
    ('Otra')
ON CONFLICT (nombre) DO NOTHING;

-- 4. Habilitar RLS
ALTER TABLE marcas ENABLE ROW LEVEL SECURITY;

-- 5. Políticas de acceso (CORREGIDAS)
-- Política para SELECT (todos pueden ver)
CREATE POLICY "marcas_select_policy"
ON marcas FOR SELECT
TO authenticated
USING (true);

-- Política para INSERT (admins)
CREATE POLICY "marcas_insert_policy"
ON marcas FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM empleados 
        WHERE empleados.id = auth.uid() AND empleados.es_admin = true
    )
);

-- Política para UPDATE (admins)
CREATE POLICY "marcas_update_policy"
ON marcas FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM empleados 
        WHERE empleados.id = auth.uid() AND empleados.es_admin = true
    )
);

-- Política para DELETE (admins)
CREATE POLICY "marcas_delete_policy"
ON marcas FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM empleados 
        WHERE empleados.id = auth.uid() AND empleados.es_admin = true
    )
);

COMMENT ON TABLE marcas IS 'Catálogo de marcas para equipos de inventario';
