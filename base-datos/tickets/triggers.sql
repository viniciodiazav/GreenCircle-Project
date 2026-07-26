-- Folio: PREFIJO-YYYYMMDD-correlativo del día, mismo patrón que el código
-- de pacas (ver base-datos/pacas/triggers.sql). Quien inserta el ticket
-- (el trigger de generar_ticket_al_cerrar_movimiento, más abajo) nunca manda
-- folio explícito -- lo arma este trigger antes del INSERT.
CREATE OR REPLACE FUNCTION generar_folio_ticket_venta()
RETURNS TRIGGER AS $$
DECLARE
    correlativo INTEGER;
BEGIN
    SELECT count(*) + 1 INTO correlativo
    FROM ticket_venta
    WHERE fecha::date = NEW.fecha::date;

    NEW.folio := 'V-' || to_char(NEW.fecha, 'YYYYMMDD') || '-' || lpad(correlativo::text, 2, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_generar_folio_ticket_venta ON ticket_venta;

CREATE TRIGGER trg_generar_folio_ticket_venta
    BEFORE INSERT ON ticket_venta
    FOR EACH ROW
    EXECUTE FUNCTION generar_folio_ticket_venta();

CREATE OR REPLACE FUNCTION generar_folio_ticket_compra()
RETURNS TRIGGER AS $$
DECLARE
    correlativo INTEGER;
BEGIN
    SELECT count(*) + 1 INTO correlativo
    FROM ticket_compra
    WHERE fecha::date = NEW.fecha::date;

    NEW.folio := 'C-' || to_char(NEW.fecha, 'YYYYMMDD') || '-' || lpad(correlativo::text, 2, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_generar_folio_ticket_compra ON ticket_compra;

CREATE TRIGGER trg_generar_folio_ticket_compra
    BEFORE INSERT ON ticket_compra
    FOR EACH ROW
    EXECUTE FUNCTION generar_folio_ticket_compra();

-- Al cerrar un movimiento se genera su ticket automáticamente: ticket_venta
-- si es SALIDA, ticket_compra si es ENTRADA. Cliente/proveedor y materiales
-- se sacan de los detalles ya existentes -- por la regla de "un solo
-- proveedor/cliente por movimiento" (ver movimientos/triggers.sql) todos los
-- detalles comparten el mismo, así que basta tomar cualquiera. El trigger
-- validar_movimiento_no_vacio (también en movimientos/triggers.sql) ya
-- garantiza que haya al menos un detalle al llegar aquí.
CREATE OR REPLACE FUNCTION generar_ticket_al_cerrar_movimiento()
RETURNS TRIGGER AS $$
DECLARE
    cliente_nombre    TEXT;
    proveedor_nombre  TEXT;
    lista_materiales  TEXT[];
    total_pacas       INTEGER;
BEGIN
    IF NEW.cerrado = true AND OLD.cerrado = false THEN
        IF NEW.tipo = 'SALIDA' THEN
            SELECT c.nombre INTO cliente_nombre
            FROM detalle_salida ds
            JOIN clientes c ON c.id = ds.cliente_id
            WHERE ds.movimiento_id = NEW.id
            LIMIT 1;

            SELECT array_agg(DISTINCT m.nombre) INTO lista_materiales
            FROM pacas p
            JOIN detalle_salida ds ON ds.id = p.detalle_salida_id
            JOIN materiales m ON m.id = p.material_id
            WHERE ds.movimiento_id = NEW.id;

            SELECT count(*) INTO total_pacas
            FROM pacas p
            JOIN detalle_salida ds ON ds.id = p.detalle_salida_id
            WHERE ds.movimiento_id = NEW.id;

            INSERT INTO ticket_venta (movimiento_id, cliente, cantidad_pacas, materiales, fecha)
            VALUES (NEW.id, cliente_nombre, total_pacas, COALESCE(lista_materiales, ARRAY[]::TEXT[]), now());

        ELSIF NEW.tipo = 'ENTRADA' THEN
            SELECT pr.nombre INTO proveedor_nombre
            FROM detalle_entrada de
            JOIN proveedores pr ON pr.id = de.proveedor_id
            WHERE de.movimiento_id = NEW.id
            LIMIT 1;

            SELECT array_agg(DISTINCT m.nombre) INTO lista_materiales
            FROM detalle_entrada de
            JOIN materiales m ON m.id = de.material_id
            WHERE de.movimiento_id = NEW.id;

            INSERT INTO ticket_compra (movimiento_id, proveedor, materiales, fecha)
            VALUES (NEW.id, proveedor_nombre, COALESCE(lista_materiales, ARRAY[]::TEXT[]), now());
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_generar_ticket_al_cerrar ON movimientos;

CREATE TRIGGER trg_generar_ticket_al_cerrar
    AFTER UPDATE OF cerrado ON movimientos
    FOR EACH ROW
    EXECUTE FUNCTION generar_ticket_al_cerrar_movimiento();
