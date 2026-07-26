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

-- Corrección (agregada 2026-07-26): si se edita peso_bruto/tara/descuento de
-- un detalle_entrada (solo permitido mientras el movimiento sigue abierto,
-- ver backend), peso_neto se recalcula solo (columna GENERATED) y aquí se
-- aplica el DELTA (NEW.peso_neto - OLD.peso_neto, puede ser negativo) al
-- inventario, dejando la corrección anotada en historial_kg -- mismo
-- principio que un ajuste manual, pero automático.
CREATE OR REPLACE FUNCTION sincronizar_inventario_entrada_editada()
RETURNS TRIGGER AS $$
DECLARE
    peso_previo NUMERIC(12, 2);
    delta       NUMERIC(12, 2);
BEGIN
    delta := NEW.peso_neto - OLD.peso_neto;
    IF delta = 0 THEN
        RETURN NEW;
    END IF;

    SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = NEW.material_id;
    peso_previo := COALESCE(peso_previo, 0);

    UPDATE inventario
        SET peso_total = peso_total + delta,
            actualizado_en = now()
        WHERE material_id = NEW.material_id;

    IF NOT FOUND THEN
        INSERT INTO inventario (material_id, peso_total, actualizado_en)
        VALUES (NEW.material_id, delta, now());
    END IF;

    INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio)
    VALUES (NEW.material_id, peso_previo, peso_previo + delta, now());

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sincronizar_inventario_entrada_editada ON detalle_entrada;

CREATE TRIGGER trg_sincronizar_inventario_entrada_editada
    AFTER UPDATE OF peso_bruto, tara, descuento ON detalle_entrada
    FOR EACH ROW
    EXECUTE FUNCTION sincronizar_inventario_entrada_editada();

-- Cancelación (agregada 2026-07-26): al cancelar (borrar) un detalle_entrada
-- -- solo permitido mientras el movimiento sigue abierto, ver
-- movimientos/triggers.sql -- se revierte lo que había sumado: resta
-- OLD.peso_neto del inventario y lo anota en historial_kg. Si el inventario
-- ya se usó (ej. se compactó una paca con ese material) y revertir dejaría
-- peso_total en negativo, el CHECK (peso_total >= 0) rechaza la cancelación
-- -- no se puede cancelar una entrada cuyo material ya se movió.
CREATE OR REPLACE FUNCTION revertir_inventario_entrada_cancelada()
RETURNS TRIGGER AS $$
DECLARE
    peso_previo NUMERIC(12, 2);
BEGIN
    SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = OLD.material_id;
    peso_previo := COALESCE(peso_previo, 0);

    UPDATE inventario
        SET peso_total = peso_total - OLD.peso_neto,
            actualizado_en = now()
        WHERE material_id = OLD.material_id;

    INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio)
    VALUES (OLD.material_id, peso_previo, peso_previo - OLD.peso_neto, now());

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_revertir_inventario_entrada_cancelada ON detalle_entrada;

CREATE TRIGGER trg_revertir_inventario_entrada_cancelada
    AFTER DELETE ON detalle_entrada
    FOR EACH ROW
    EXECUTE FUNCTION revertir_inventario_entrada_cancelada();

-- Al registrarse una paca, su peso (aproximado o real) se resta del
-- inventario de material suelto -- se asume que ese material ya se
-- compactó y dejó de estar "suelto". Si el material no tiene inventario
-- suficiente registrado, el CHECK (peso_total >= 0) de la tabla inventario
-- rechaza la operación (no se puede compactar más de lo que hay).
--
-- NOTA: usa UPDATE explícito (con INSERT de respaldo si no existe fila),
-- NO "INSERT ... ON CONFLICT DO UPDATE" -- Postgres valida el CHECK contra
-- el valor propuesto del INSERT ANTES de detectar el conflicto, así que un
-- delta negativo (como este) siempre fallaría el CHECK aunque el resultado
-- final del UPDATE sí fuera válido (ej. 15.50 - 15.50 = 0, que sí cumple
-- >= 0, pero el INSERT probaría con -15.50 primero y reventaría el CHECK
-- antes de llegar a la resolución del conflicto).
CREATE OR REPLACE FUNCTION sincronizar_inventario_paca_registrada()
RETURNS TRIGGER AS $$
DECLARE
    peso_previo NUMERIC(12, 2);
BEGIN
    SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = NEW.material_id;
    peso_previo := COALESCE(peso_previo, 0);

    UPDATE inventario
        SET peso_total = peso_total - NEW.peso,
            actualizado_en = now()
        WHERE material_id = NEW.material_id;

    IF NOT FOUND THEN
        INSERT INTO inventario (material_id, peso_total, actualizado_en)
        VALUES (NEW.material_id, -NEW.peso, now());
    END IF;

    INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio)
    VALUES (NEW.material_id, peso_previo, peso_previo - NEW.peso, now());

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sincronizar_inventario_paca_registrada ON pacas;

CREATE TRIGGER trg_sincronizar_inventario_paca_registrada
    AFTER INSERT ON pacas
    FOR EACH ROW
    EXECUTE FUNCTION sincronizar_inventario_paca_registrada();

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

-- Cancelación (agregada 2026-07-26): cuando se cancela el detalle_salida que
-- vendió la paca (ver movimientos/triggers.sql), la paca vuelve a
-- en_inventario = true -- suma 1 de vuelta a inventario_pacas, reverso
-- exacto de sincronizar_inventario_pacas_baja.
CREATE OR REPLACE FUNCTION reactivar_inventario_pacas()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE inventario_pacas
        SET cantidad = cantidad + 1,
            actualizado_en = now()
        WHERE material_id = NEW.material_id;

    IF NOT FOUND THEN
        INSERT INTO inventario_pacas (material_id, cantidad, actualizado_en)
        VALUES (NEW.material_id, 1, now());
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_reactivar_inventario_pacas ON pacas;

CREATE TRIGGER trg_reactivar_inventario_pacas
    AFTER UPDATE OF en_inventario ON pacas
    FOR EACH ROW
    WHEN (OLD.en_inventario = false AND NEW.en_inventario = true)
    EXECUTE FUNCTION reactivar_inventario_pacas();

-- Cada ajuste manual (ver ajustes_inventario en schema.sql) aplica su delta
-- (peso_ajuste, +/-) al inventario del material correspondiente, y queda
-- anotado también en historial_kg -- una sola línea de tiempo con entradas,
-- pacas y ajustes juntos. Mismo UPDATE explícito que la función de arriba,
-- por la misma razón (un ajuste negativo rompería el patrón ON CONFLICT).
CREATE OR REPLACE FUNCTION sincronizar_inventario_ajuste()
RETURNS TRIGGER AS $$
DECLARE
    peso_previo NUMERIC(12, 2);
BEGIN
    SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = NEW.material_id;
    peso_previo := COALESCE(peso_previo, 0);

    UPDATE inventario
        SET peso_total = peso_total + NEW.peso_ajuste,
            actualizado_en = now()
        WHERE material_id = NEW.material_id;

    IF NOT FOUND THEN
        INSERT INTO inventario (material_id, peso_total, actualizado_en)
        VALUES (NEW.material_id, NEW.peso_ajuste, now());
    END IF;

    INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio)
    VALUES (NEW.material_id, peso_previo, peso_previo + NEW.peso_ajuste, now());

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sincronizar_inventario_ajuste ON ajustes_inventario;

CREATE TRIGGER trg_sincronizar_inventario_ajuste
    AFTER INSERT ON ajustes_inventario
    FOR EACH ROW
    EXECUTE FUNCTION sincronizar_inventario_ajuste();
