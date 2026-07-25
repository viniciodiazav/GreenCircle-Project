-- Cada paca que se registra queda anotada en su historial como ALTA.
CREATE OR REPLACE FUNCTION registrar_historial_paca_alta()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO historial_pacas (paca_id, evento, fecha)
    VALUES (NEW.id, 'ALTA', now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_historial_paca_alta ON pacas;

CREATE TRIGGER trg_historial_paca_alta
    AFTER INSERT ON pacas
    FOR EACH ROW
    EXECUTE FUNCTION registrar_historial_paca_alta();

-- Cuando una paca se marca como vendida (en_inventario true -> false), queda
-- anotada en su historial como VENTA, ligada al detalle_salida exacto.
CREATE OR REPLACE FUNCTION registrar_historial_paca_venta()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO historial_pacas (paca_id, evento, detalle_salida_id, fecha)
    VALUES (NEW.id, 'VENTA', NEW.detalle_salida_id, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_historial_paca_venta ON pacas;

CREATE TRIGGER trg_historial_paca_venta
    AFTER UPDATE OF en_inventario ON pacas
    FOR EACH ROW
    WHEN (OLD.en_inventario = true AND NEW.en_inventario = false)
    EXECUTE FUNCTION registrar_historial_paca_venta();
