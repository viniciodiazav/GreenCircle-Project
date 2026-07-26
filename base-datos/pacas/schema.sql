-- Dominio pacas: unidad compactada que sí se vende (el centro no vende
-- material suelto). detalle_salida_id amarra la paca a la venta exacta en
-- la que salió -- necesario para saber cuáles pacas se vendieron, no solo
-- cuántas.
--
-- codigo NO lo manda quien registra la paca -- lo arma un trigger (ver
-- triggers.sql) a partir del código del material + fecha + correlativo del
-- día, así que aquí solo se declara NOT NULL UNIQUE como cualquier columna
-- ya resuelta al momento del INSERT.

CREATE TABLE IF NOT EXISTS pacas (
    id                SERIAL PRIMARY KEY,
    codigo            VARCHAR(30) NOT NULL UNIQUE,
    material_id       INTEGER NOT NULL REFERENCES materiales(id),
    peso              NUMERIC(10, 2) NOT NULL CHECK (peso > 0),
    en_inventario     BOOLEAN NOT NULL DEFAULT true,
    fecha_registro    TIMESTAMPTZ NOT NULL DEFAULT now(),
    detalle_salida_id INTEGER REFERENCES detalle_salida(id),
    CHECK (
        (en_inventario = true  AND detalle_salida_id IS NULL)
        OR
        (en_inventario = false AND detalle_salida_id IS NOT NULL)
    )
);

-- Historial de eventos de cada paca (mismo patrón que historial_precios):
-- log append-only, lo llenan los triggers de este archivo, nunca el backend.
-- CANCELACION (agregado 2026-07-26): cuando se cancela el detalle_salida que
-- vendió la paca (ver movimientos/triggers.sql), la venta se revierte y
-- queda anotada aquí -- nunca se borra el evento VENTA original, la
-- cancelación es una línea nueva, mismo principio append-only. ON DELETE SET
-- NULL en detalle_salida_id: al cancelarse (borrarse) el detalle_salida, el
-- historial de sus pacas sigue existiendo, solo pierde el link al ya no
-- existente.
CREATE TABLE IF NOT EXISTS historial_pacas (
    id                SERIAL PRIMARY KEY,
    paca_id           INTEGER NOT NULL REFERENCES pacas(id) ON DELETE CASCADE,
    evento            VARCHAR(15) NOT NULL CHECK (evento IN ('ALTA', 'VENTA', 'CANCELACION')),
    detalle_salida_id INTEGER REFERENCES detalle_salida(id) ON DELETE SET NULL,
    fecha             TIMESTAMPTZ NOT NULL DEFAULT now()
);
