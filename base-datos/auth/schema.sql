-- Dominio auth: varios usuarios con los mismos permisos (sin roles) --
-- decisión explícita del usuario, 2026-07-26: la idea es saber quién hizo
-- qué (ver creado_por en movimientos/detalle_entrada/detalle_salida/
-- ajustes_inventario y usuario_id en historial_kg/historial_pacas), no
-- restringir qué puede hacer cada quien. `activo` permite dar de baja una
-- cuenta sin borrarla (y sin perder las referencias de creado_por).

CREATE TABLE IF NOT EXISTS usuarios (
    id              SERIAL PRIMARY KEY,
    usuario         VARCHAR(50) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT true
);
