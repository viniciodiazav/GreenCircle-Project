-- Dominio auth: usuarios con rol (agregado 2026-07-27, revierte la decisión
-- "sin roles" del 2026-07-26 -- el usuario cambió de opinión porque quiere
-- una UI distinta por rol en el frontend). `activo` permite dar de baja una
-- cuenta sin borrarla (y sin perder las referencias de creado_por en
-- movimientos/detalle_entrada/detalle_salida/ajustes_inventario).
--
-- 'operador' es el default: cubre el trabajo del día a día (ver catálogos,
-- crear/editar/cerrar/cancelar movimientos, detalles y pacas). Solo
-- 'administrador' puede: precios de materiales, alta/baja/creación de
-- materiales-proveedores-clientes, ajustes de inventario, y gestión de
-- usuarios (ver backend/app/core/security.py, require_admin).
CREATE TABLE IF NOT EXISTS usuarios (
    id              SERIAL PRIMARY KEY,
    usuario         VARCHAR(50) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    activo          BOOLEAN NOT NULL DEFAULT true,
    rol             VARCHAR(20) NOT NULL DEFAULT 'operador'
                        CHECK (rol IN ('operador', 'administrador'))
);
