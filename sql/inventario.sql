-- =============================================
-- TABLAS DE INVENTARIO DE EQUIPOS
-- Ejecutar en Supabase SQL Editor
-- =============================================

-- Tabla principal de equipos
CREATE TABLE IF NOT EXISTS equipos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tipo VARCHAR(50) NOT NULL CHECK (tipo IN ('laptop', 'desktop', 'monitor', 'teclado', 'mouse', 'headset', 'telefono', 'impresora', 'otro')),
    marca VARCHAR(100),
    modelo VARCHAR(100),
    numero_serie VARCHAR(100) UNIQUE,
    numero_activo VARCHAR(50),
    especificaciones TEXT,
    estado VARCHAR(20) DEFAULT 'disponible' CHECK (estado IN ('disponible', 'asignado', 'en_reparacion', 'baja')),
    empleado_id UUID REFERENCES empleados(id) ON DELETE SET NULL,
    fecha_asignacion DATE,
    fecha_compra DATE,
    proveedor VARCHAR(100),
    costo DECIMAL(10,2),
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de historial de asignaciones
CREATE TABLE IF NOT EXISTS historial_equipos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    equipo_id UUID REFERENCES equipos(id) ON DELETE CASCADE,
    empleado_id UUID REFERENCES empleados(id) ON DELETE SET NULL,
    fecha_asignacion DATE NOT NULL,
    fecha_devolucion DATE,
    notas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_equipos_estado ON equipos(estado);
CREATE INDEX IF NOT EXISTS idx_equipos_tipo ON equipos(tipo);
CREATE INDEX IF NOT EXISTS idx_equipos_empleado ON equipos(empleado_id);
CREATE INDEX IF NOT EXISTS idx_historial_equipo ON historial_equipos(equipo_id);
CREATE INDEX IF NOT EXISTS idx_historial_empleado ON historial_equipos(empleado_id);

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_equipos_updated_at
    BEFORE UPDATE ON equipos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================

-- Habilitar RLS
ALTER TABLE equipos ENABLE ROW LEVEL SECURITY;
ALTER TABLE historial_equipos ENABLE ROW LEVEL SECURITY;

-- Políticas para equipos (todos los usuarios autenticados pueden ver)
CREATE POLICY "Usuarios autenticados pueden ver equipos"
ON equipos FOR SELECT
TO authenticated
USING (true);

-- Solo admins pueden insertar/actualizar/eliminar equipos
CREATE POLICY "Admins pueden insertar equipos"
ON equipos FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM empleados
        WHERE empleados.id = auth.uid()
        AND empleados.es_admin = true
    )
);

CREATE POLICY "Admins pueden actualizar equipos"
ON equipos FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM empleados
        WHERE empleados.id = auth.uid()
        AND empleados.es_admin = true
    )
);

CREATE POLICY "Admins pueden eliminar equipos"
ON equipos FOR DELETE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM empleados
        WHERE empleados.id = auth.uid()
        AND empleados.es_admin = true
    )
);

-- Políticas para historial
CREATE POLICY "Usuarios autenticados pueden ver historial"
ON historial_equipos FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "Admins pueden insertar historial"
ON historial_equipos FOR INSERT
TO authenticated
WITH CHECK (
    EXISTS (
        SELECT 1 FROM empleados
        WHERE empleados.id = auth.uid()
        AND empleados.es_admin = true
    )
);

CREATE POLICY "Admins pueden actualizar historial"
ON historial_equipos FOR UPDATE
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM empleados
        WHERE empleados.id = auth.uid()
        AND empleados.es_admin = true
    )
);

-- =============================================
-- DATOS DE EJEMPLO (OPCIONAL)
-- =============================================

-- Puedes descomentar las siguientes líneas para agregar datos de prueba:

/*
INSERT INTO equipos (tipo, marca, modelo, numero_serie, numero_activo, especificaciones, estado) VALUES
('laptop', 'Dell', 'Latitude 5520', 'DELL001ABC', 'ACT-001', 'Intel i5-1135G7, 16GB RAM, 512GB SSD', 'disponible'),
('laptop', 'HP', 'ProBook 450 G8', 'HP002XYZ', 'ACT-002', 'Intel i7-1165G7, 16GB RAM, 256GB SSD', 'disponible'),
('monitor', 'LG', '24MK430H', 'LG003MON', 'ACT-003', '24 pulgadas, Full HD, IPS', 'disponible'),
('teclado', 'Logitech', 'K120', 'LOG004KEY', 'ACT-004', 'Teclado USB estándar', 'disponible'),
('mouse', 'Logitech', 'M90', 'LOG005MOU', 'ACT-005', 'Mouse USB óptico', 'disponible');
*/
