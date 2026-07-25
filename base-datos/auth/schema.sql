-- Dominio auth: administrador único de la app.

CREATE TABLE IF NOT EXISTS admin (
    id              SERIAL PRIMARY KEY,
    usuario         VARCHAR(50) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL
);
