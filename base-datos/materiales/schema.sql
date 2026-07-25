-- Dominio materiales: catálogo de precios de compra e historial de cambios.

CREATE TABLE IF NOT EXISTS materiales (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL UNIQUE,
    codigo          VARCHAR(30) NOT NULL UNIQUE,
    unidad          VARCHAR(20) NOT NULL DEFAULT 'kg',
    precio_actual   NUMERIC(10, 2) NOT NULL CHECK (precio_actual > 0),
    activo          BOOLEAN NOT NULL DEFAULT true,
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS historial_precios (
    id              SERIAL PRIMARY KEY,
    material_id     INTEGER NOT NULL REFERENCES materiales(id) ON DELETE CASCADE,
    precio_anterior NUMERIC(10, 2) NOT NULL,
    precio_nuevo    NUMERIC(10, 2) NOT NULL,
    fecha_cambio    TIMESTAMPTZ NOT NULL DEFAULT now()
);
