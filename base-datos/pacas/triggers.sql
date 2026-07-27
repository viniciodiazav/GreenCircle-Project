-- Quien registra una paca no manda el código -- se arma solo:
-- {codigo_material}-{fecha YYYYMMDD}-{correlativo del día para ese material}.
-- Ej. segunda paca de Cartón registrada el 2026-07-25: CART-20260725-02.
CREATE OR REPLACE FUNCTION generar_codigo_paca()
RETURNS TRIGGER AS $$
DECLARE
    codigo_mat  VARCHAR(30);
    correlativo INTEGER;
BEGIN
    SELECT codigo INTO codigo_mat FROM materiales WHERE id = NEW.material_id;

    SELECT count(*) + 1 INTO correlativo
    FROM pacas
    WHERE material_id = NEW.material_id
      AND fecha_registro::date = CURRENT_DATE;

    NEW.codigo := codigo_mat || '-' || to_char(now(), 'YYYYMMDD') || '-' || lpad(correlativo::text, 2, '0');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_generar_codigo_paca ON pacas;

CREATE TRIGGER trg_generar_codigo_paca
    BEFORE INSERT ON pacas
    FOR EACH ROW
    EXECUTE FUNCTION generar_codigo_paca();

-- No se puede registrar una paca de un material dado de baja (activo =
-- false) -- mismo principio que en detalle_entrada/detalle_salida.
CREATE OR REPLACE FUNCTION validar_material_activo_paca()
RETURNS TRIGGER AS $$
DECLARE
    material_activo BOOLEAN;
BEGIN
    SELECT activo INTO material_activo FROM materiales WHERE id = NEW.material_id;
    IF NOT material_activo THEN
        RAISE EXCEPTION 'El material % está inactivo', NEW.material_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validar_material_activo_paca ON pacas;

CREATE TRIGGER trg_validar_material_activo_paca
    BEFORE INSERT ON pacas
    FOR EACH ROW
    EXECUTE FUNCTION validar_material_activo_paca();

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

-- Cuando se cancela el detalle_salida que vendió la paca (ver
-- movimientos/triggers.sql, liberar_pacas_al_cancelar_detalle_salida), la
-- paca vuelve a en_inventario = true y queda anotada aquí como CANCELACION,
-- ligada al detalle_salida que se está cancelando (OLD.detalle_salida_id --
-- para cuando este trigger corre, NEW.detalle_salida_id ya es NULL). Nunca
-- se borra el evento VENTA original: la cancelación es una línea nueva.
-- usuario_id sale de current_setting('app.usuario_actual', true), seteado
-- por el backend (SET LOCAL) antes del DELETE del detalle_salida que
-- disparó esta cadena -- ver app.core.database.set_usuario_actual.
CREATE OR REPLACE FUNCTION registrar_historial_paca_cancelacion()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO historial_pacas (paca_id, evento, detalle_salida_id, fecha, usuario_id)
    VALUES (
        NEW.id, 'CANCELACION', OLD.detalle_salida_id, now(),
        NULLIF(current_setting('app.usuario_actual', true), '')::INTEGER
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_historial_paca_cancelacion ON pacas;

CREATE TRIGGER trg_historial_paca_cancelacion
    AFTER UPDATE OF en_inventario ON pacas
    FOR EACH ROW
    WHEN (OLD.en_inventario = false AND NEW.en_inventario = true)
    EXECUTE FUNCTION registrar_historial_paca_cancelacion();
