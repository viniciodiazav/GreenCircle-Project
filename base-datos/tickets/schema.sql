-- Dominio tickets: comprobantes autogenerados al cerrar un movimiento.
-- El backend nunca escribe aquí -- se llenan solos vía trigger en
-- movimientos (ver triggers.sql de este mismo dominio) cuando un movimiento
-- pasa de abierto a cerrado. Mismo principio que historial_precios/kg/pacas.

CREATE TABLE IF NOT EXISTS ticket_venta (
    id             SERIAL PRIMARY KEY,
    movimiento_id  INTEGER NOT NULL UNIQUE REFERENCES movimientos(id),
    folio          VARCHAR(30) NOT NULL UNIQUE,
    cliente        TEXT NOT NULL,
    cantidad_pacas INTEGER NOT NULL,
    materiales     TEXT[] NOT NULL,
    fecha          TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_compra (
    id             SERIAL PRIMARY KEY,
    movimiento_id  INTEGER NOT NULL UNIQUE REFERENCES movimientos(id),
    folio          VARCHAR(30) NOT NULL UNIQUE,
    proveedor      TEXT NOT NULL,
    materiales     TEXT[] NOT NULL,
    fecha          TIMESTAMPTZ NOT NULL
);
