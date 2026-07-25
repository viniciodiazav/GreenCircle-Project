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

-- Un detalle no puede referenciar un proveedor o material dado de baja
-- (activo = false) -- el soft delete no es solo cosmético.
CREATE OR REPLACE FUNCTION validar_activos_detalle_entrada()
RETURNS TRIGGER AS $$
DECLARE
    proveedor_activo BOOLEAN;
    material_activo  BOOLEAN;
BEGIN
    SELECT activo INTO proveedor_activo FROM proveedores WHERE id = NEW.proveedor_id;
    IF NOT proveedor_activo THEN
        RAISE EXCEPTION 'El proveedor % está inactivo', NEW.proveedor_id;
    END IF;

    SELECT activo INTO material_activo FROM materiales WHERE id = NEW.material_id;
    IF NOT material_activo THEN
        RAISE EXCEPTION 'El material % está inactivo', NEW.material_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_activos_entrada ON detalle_entrada;

CREATE TRIGGER trg_validar_activos_entrada
    BEFORE INSERT ON detalle_entrada
    FOR EACH ROW
    EXECUTE FUNCTION validar_activos_detalle_entrada();

-- Mismo principio para detalle_salida: no se puede vender a un cliente dado
-- de baja.
CREATE OR REPLACE FUNCTION validar_activo_detalle_salida()
RETURNS TRIGGER AS $$
DECLARE
    cliente_activo BOOLEAN;
BEGIN
    SELECT activo INTO cliente_activo FROM clientes WHERE id = NEW.cliente_id;
    IF NOT cliente_activo THEN
        RAISE EXCEPTION 'El cliente % está inactivo', NEW.cliente_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_activo_salida ON detalle_salida;

CREATE TRIGGER trg_validar_activo_salida
    BEFORE INSERT ON detalle_salida
    FOR EACH ROW
    EXECUTE FUNCTION validar_activo_detalle_salida();
