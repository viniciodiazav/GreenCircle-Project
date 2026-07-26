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

-- Regla de negocio: todos los detalles de un mismo movimiento deben ser del
-- mismo proveedor (entrada) o del mismo cliente (salida) -- un movimiento no
-- puede mezclar dos proveedores/clientes distintos en sus líneas.
CREATE OR REPLACE FUNCTION validar_mismo_proveedor_detalle_entrada()
RETURNS TRIGGER AS $$
DECLARE
    proveedor_existente INTEGER;
BEGIN
    SELECT proveedor_id INTO proveedor_existente
    FROM detalle_entrada
    WHERE movimiento_id = NEW.movimiento_id
    LIMIT 1;

    IF proveedor_existente IS NOT NULL AND proveedor_existente <> NEW.proveedor_id THEN
        RAISE EXCEPTION 'El movimiento % ya tiene detalles del proveedor %, no puede mezclar proveedores', NEW.movimiento_id, proveedor_existente;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_mismo_proveedor_entrada ON detalle_entrada;

CREATE TRIGGER trg_validar_mismo_proveedor_entrada
    BEFORE INSERT ON detalle_entrada
    FOR EACH ROW
    EXECUTE FUNCTION validar_mismo_proveedor_detalle_entrada();

CREATE OR REPLACE FUNCTION validar_mismo_cliente_detalle_salida()
RETURNS TRIGGER AS $$
DECLARE
    cliente_existente INTEGER;
BEGIN
    SELECT cliente_id INTO cliente_existente
    FROM detalle_salida
    WHERE movimiento_id = NEW.movimiento_id
    LIMIT 1;

    IF cliente_existente IS NOT NULL AND cliente_existente <> NEW.cliente_id THEN
        RAISE EXCEPTION 'El movimiento % ya tiene detalles del cliente %, no puede mezclar clientes', NEW.movimiento_id, cliente_existente;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_mismo_cliente_salida ON detalle_salida;

CREATE TRIGGER trg_validar_mismo_cliente_salida
    BEFORE INSERT ON detalle_salida
    FOR EACH ROW
    EXECUTE FUNCTION validar_mismo_cliente_detalle_salida();

-- Un movimiento sin ningún detalle no puede cerrarse -- no habría de dónde
-- sacar el proveedor/cliente ni los materiales para armar su ticket
-- (ver base-datos/tickets/triggers.sql).
CREATE OR REPLACE FUNCTION validar_movimiento_no_vacio()
RETURNS TRIGGER AS $$
DECLARE
    tiene_detalles BOOLEAN;
BEGIN
    IF NEW.cerrado = true AND OLD.cerrado = false THEN
        IF NEW.tipo = 'ENTRADA' THEN
            SELECT EXISTS(SELECT 1 FROM detalle_entrada WHERE movimiento_id = NEW.id) INTO tiene_detalles;
        ELSE
            SELECT EXISTS(SELECT 1 FROM detalle_salida WHERE movimiento_id = NEW.id) INTO tiene_detalles;
        END IF;

        IF NOT tiene_detalles THEN
            RAISE EXCEPTION 'El movimiento % no tiene detalles, no se puede cerrar', NEW.id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_movimiento_no_vacio ON movimientos;

CREATE TRIGGER trg_validar_movimiento_no_vacio
    BEFORE UPDATE OF cerrado ON movimientos
    FOR EACH ROW
    EXECUTE FUNCTION validar_movimiento_no_vacio();

-- Cancelación de detalle_salida (agregada 2026-07-26, solo permitida por el
-- backend mientras el movimiento sigue abierto): antes de borrar la fila,
-- libera las pacas que vendía -- en_inventario = true, detalle_salida_id =
-- NULL -- para que la FK pacas.detalle_salida_id no bloquee el DELETE y para
-- que esas pacas vuelvan a estar disponibles para vender. El UPDATE de
-- pacas dispara a su vez trg_reactivar_inventario_pacas y
-- trg_historial_paca_cancelacion (ver inventario/triggers.sql y
-- pacas/triggers.sql).
CREATE OR REPLACE FUNCTION liberar_pacas_al_cancelar_detalle_salida()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE pacas
        SET en_inventario = true,
            detalle_salida_id = NULL
        WHERE detalle_salida_id = OLD.id;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_liberar_pacas_al_cancelar_detalle_salida ON detalle_salida;

CREATE TRIGGER trg_liberar_pacas_al_cancelar_detalle_salida
    BEFORE DELETE ON detalle_salida
    FOR EACH ROW
    EXECUTE FUNCTION liberar_pacas_al_cancelar_detalle_salida();
