-- Dominio movimientos: cabecera de ENTRADA/SALIDA y sus líneas de detalle.
--
-- El truco de UNIQUE (id, tipo) + FK compuesta en cada detalle es lo que le
-- permite a Postgres garantizar, sin trigger, que un detalle_entrada solo
-- pueda apuntar a un movimiento tipo ENTRADA (y un detalle_salida a uno tipo
-- SALIDA) -- regla de negocio: "cada detalle pertenece a un solo movimiento
-- de su mismo tipo".

CREATE TABLE IF NOT EXISTS movimientos (
    id          SERIAL PRIMARY KEY,
    tipo        VARCHAR(10) NOT NULL CHECK (tipo IN ('ENTRADA', 'SALIDA')),
    fecha       TIMESTAMPTZ NOT NULL DEFAULT now(),
    cerrado     BOOLEAN NOT NULL DEFAULT false,
    descripcion TEXT,
    UNIQUE (id, tipo)
);

CREATE TABLE IF NOT EXISTS detalle_entrada (
    id              SERIAL PRIMARY KEY,
    movimiento_id   INTEGER NOT NULL,
    tipo_movimiento VARCHAR(10) NOT NULL DEFAULT 'ENTRADA' CHECK (tipo_movimiento = 'ENTRADA'),
    proveedor_id    INTEGER NOT NULL REFERENCES proveedores(id),
    material_id     INTEGER NOT NULL REFERENCES materiales(id),
    peso_bruto      NUMERIC(10, 2) NOT NULL CHECK (peso_bruto > 0),
    tara            NUMERIC(10, 2) NOT NULL CHECK (tara >= 0),
    peso_neto       NUMERIC(10, 2) GENERATED ALWAYS AS (peso_bruto - tara) STORED,
    precio_compra   NUMERIC(10, 2) NOT NULL CHECK (precio_compra > 0),
    fecha           TIMESTAMPTZ NOT NULL DEFAULT now(),
    descripcion     TEXT,
    CHECK (peso_bruto > tara),
    FOREIGN KEY (movimiento_id, tipo_movimiento) REFERENCES movimientos (id, tipo)
);

CREATE TABLE IF NOT EXISTS detalle_salida (
    id              SERIAL PRIMARY KEY,
    movimiento_id   INTEGER NOT NULL,
    tipo_movimiento VARCHAR(10) NOT NULL DEFAULT 'SALIDA' CHECK (tipo_movimiento = 'SALIDA'),
    cliente_id      INTEGER NOT NULL REFERENCES clientes(id),
    precio_venta    NUMERIC(10, 2) NOT NULL CHECK (precio_venta > 0),
    fecha           TIMESTAMPTZ NOT NULL DEFAULT now(),
    descripcion     TEXT,
    FOREIGN KEY (movimiento_id, tipo_movimiento) REFERENCES movimientos (id, tipo)
);

-- cantidad_pacas no es columna: se calcula con
-- SELECT COUNT(*) FROM pacas WHERE detalle_salida_id = <detalle_salida.id>
