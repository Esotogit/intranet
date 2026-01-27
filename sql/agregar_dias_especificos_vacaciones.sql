-- =============================================
-- AGREGAR CAMPO dias_especificos A VACACIONES
-- =============================================

-- Agregar columna para almacenar días específicos seleccionados
-- Se almacena como array de texto con las fechas en formato YYYY-MM-DD
ALTER TABLE vacaciones 
ADD COLUMN IF NOT EXISTS dias_especificos TEXT[] DEFAULT NULL;

-- Comentario explicativo
COMMENT ON COLUMN vacaciones.dias_especificos IS 'Lista de fechas específicas seleccionadas (YYYY-MM-DD). NULL si se usó rango continuo.';
