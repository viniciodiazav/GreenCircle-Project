-- Si no se manda precio_compra explícito, se toma el snapshot del precio de
-- compra vigente en materiales -- así el detalle no pierde el precio pagado
-- aunque el catálogo cambie después.
CREATE OR REPLACE FUNCTION completar_precio_compra()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.precio_compra IS NULL THEN
        SELECT precio_actual INTO NEW.precio_compra
        FROM materiales
        WHERE id = NEW.material_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_completar_precio_compra ON detalle_entrada;

CREATE TRIGGER trg_completar_precio_compra
    BEFORE INSERT ON detalle_entrada
    FOR EACH ROW
    EXECUTE FUNCTION completar_precio_compra();

-- Un movimiento cerrado ya no acepta más líneas de detalle, sin importar el
-- tipo -- protege la integridad del cierre contable.
CREATE OR REPLACE FUNCTION bloquear_detalle_si_movimiento_cerrado()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT cerrado FROM movimientos WHERE id = NEW.movimiento_id) THEN
        RAISE EXCEPTION 'El movimiento % ya está cerrado, no se pueden agregar más detalles', NEW.movimiento_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_bloquear_cerrado_entrada ON detalle_entrada;

CREATE TRIGGER trg_bloquear_cerrado_entrada
    BEFORE INSERT ON detalle_entrada
    FOR EACH ROW
    EXECUTE FUNCTION bloquear_detalle_si_movimiento_cerrado();

DROP TRIGGER IF EXISTS trg_bloquear_cerrado_salida ON detalle_salida;

CREATE TRIGGER trg_bloquear_cerrado_salida
    BEFORE INSERT ON detalle_salida
    FOR EACH ROW
    EXECUTE FUNCTION bloquear_detalle_si_movimiento_cerrado();
