-- Dominio proveedores: contrapartes de ENTRADA (de quién se recibe material).

CREATE TABLE IF NOT EXISTS proveedores (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL,
    direccion   VARCHAR(255),
    contacto    VARCHAR(100),
    activo      BOOLEAN NOT NULL DEFAULT true
);
