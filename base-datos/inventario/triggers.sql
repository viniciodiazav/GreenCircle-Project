-- Cada detalle_entrada suma su peso_neto al inventario de material suelto
-- del material correspondiente, y deja el cambio anotado en historial_kg
-- (mismo patrón que historial_precios: log append-only vía trigger).
CREATE OR REPLACE FUNCTION sincronizar_inventario_entrada()
RETURNS TRIGGER AS $$
DECLARE
    peso_previo NUMERIC(12, 2);
BEGIN
    SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = NEW.material_id;
    peso_previo := COALESCE(peso_previo, 0);

    INSERT INTO inventario (material_id, peso_total, actualizado_en)
    VALUES (NEW.material_id, NEW.peso_neto, now())
    ON CONFLICT (material_id) DO UPDATE
        SET peso_total = inventario.peso_total + NEW.peso_neto,
            actualizado_en = now();

    INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio)
    VALUES (NEW.material_id, peso_previo, peso_previo + NEW.peso_neto, now());

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sincronizar_inventario_entrada ON detalle_entrada;

CREATE TRIGGER trg_sincronizar_inventario_entrada
    AFTER INSERT ON detalle_entrada
    FOR EACH ROW
    EXECUTE FUNCTION sincronizar_inventario_entrada();

-- Toda paca nace en_inventario = true (regla de la propia tabla pacas), así
-- que un INSERT siempre suma 1 al inventario_pacas de su material.
CREATE OR REPLACE FUNCTION sincronizar_inventario_pacas_alta()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO inventario_pacas (material_id, cantidad, actualizado_en)
    VALUES (NEW.material_id, 1, now())
    ON CONFLICT (material_id) DO UPDATE
        SET cantidad = inventario_pacas.cantidad + 1,
            actualizado_en = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sincronizar_inventario_pacas_alta ON pacas;

CREATE TRIGGER trg_sincronizar_inventario_pacas_alta
    AFTER INSERT ON pacas
    FOR EACH ROW
    EXECUTE FUNCTION sincronizar_inventario_pacas_alta();

-- Cuando una paca se marca como vendida (en_inventario true -> false), resta
-- 1 del inventario_pacas de su material.
CREATE OR REPLACE FUNCTION sincronizar_inventario_pacas_baja()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE inventario_pacas
        SET cantidad = cantidad - 1,
            actualizado_en = now()
        WHERE material_id = NEW.material_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sincronizar_inventario_pacas_baja ON pacas;

CREATE TRIGGER trg_sincronizar_inventario_pacas_baja
    AFTER UPDATE OF en_inventario ON pacas
    FOR EACH ROW
    WHEN (OLD.en_inventario = true AND NEW.en_inventario = false)
    EXECUTE FUNCTION sincronizar_inventario_pacas_baja();
