-- Registra automáticamente cada cambio de precio en el historial,
-- para que la auditoría no dependa de que el backend recuerde hacerlo.

CREATE OR REPLACE FUNCTION registrar_cambio_precio()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.precio_actual IS DISTINCT FROM OLD.precio_actual THEN
        INSERT INTO historial_precios (material_id, precio_anterior, precio_nuevo, fecha_cambio)
        VALUES (OLD.id, OLD.precio_actual, NEW.precio_actual, now());

        NEW.actualizado_en := now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_registrar_cambio_precio ON materiales;

CREATE TRIGGER trg_registrar_cambio_precio
    BEFORE UPDATE OF precio_actual ON materiales
    FOR EACH ROW
    EXECUTE FUNCTION registrar_cambio_precio();
