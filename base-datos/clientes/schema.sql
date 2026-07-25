-- Dominio clientes: contrapartes de SALIDA (a quién se vende material).

CREATE TABLE IF NOT EXISTS clientes (
    id          SERIAL PRIMARY KEY,
    nombre      VARCHAR(150) NOT NULL,
    direccion   VARCHAR(255),
    contacto    VARCHAR(100),
    activo      BOOLEAN NOT NULL DEFAULT true
);
