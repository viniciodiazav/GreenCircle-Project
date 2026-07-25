"""proveedores, clientes, movimientos, pacas, inventario

Revision ID: 541b00529aa6
Revises: 5e2ebc4a8619
Create Date: 2026-07-25 14:04:34.661915

Mirrors base-datos/{proveedores,clientes,movimientos,pacas,inventario}/*.sql
(fuente canónica y legible). Se repite aquí como statements separados porque
el driver asyncpg no admite múltiples comandos en un solo execute.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '541b00529aa6'
down_revision: Union[str, None] = '5e2ebc4a8619'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS proveedores (
            id          SERIAL PRIMARY KEY,
            nombre      VARCHAR(150) NOT NULL,
            direccion   VARCHAR(255),
            contacto    VARCHAR(100)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id          SERIAL PRIMARY KEY,
            nombre      VARCHAR(150) NOT NULL,
            direccion   VARCHAR(255),
            contacto    VARCHAR(100)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS movimientos (
            id          SERIAL PRIMARY KEY,
            tipo        VARCHAR(10) NOT NULL CHECK (tipo IN ('ENTRADA', 'SALIDA')),
            fecha       TIMESTAMPTZ NOT NULL DEFAULT now(),
            cerrado     BOOLEAN NOT NULL DEFAULT false,
            descripcion TEXT,
            UNIQUE (id, tipo)
        )
        """
    )
    op.execute(
        """
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
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS detalle_salida (
            id              SERIAL PRIMARY KEY,
            movimiento_id   INTEGER NOT NULL,
            tipo_movimiento VARCHAR(10) NOT NULL DEFAULT 'SALIDA' CHECK (tipo_movimiento = 'SALIDA'),
            cliente_id      INTEGER NOT NULL REFERENCES clientes(id),
            precio_venta    NUMERIC(10, 2) NOT NULL CHECK (precio_venta > 0),
            fecha           TIMESTAMPTZ NOT NULL DEFAULT now(),
            descripcion     TEXT,
            FOREIGN KEY (movimiento_id, tipo_movimiento) REFERENCES movimientos (id, tipo)
        )
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION completar_precio_compra()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.precio_compra IS NULL THEN
                SELECT precio_actual INTO NEW.precio_compra
                FROM materiales
                WHERE id = NEW.material_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_completar_precio_compra ON detalle_entrada")
    op.execute(
        """
        CREATE TRIGGER trg_completar_precio_compra
            BEFORE INSERT ON detalle_entrada
            FOR EACH ROW
            EXECUTE FUNCTION completar_precio_compra()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION bloquear_detalle_si_movimiento_cerrado()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (SELECT cerrado FROM movimientos WHERE id = NEW.movimiento_id) THEN
                RAISE EXCEPTION 'El movimiento % ya está cerrado, no se pueden agregar más detalles', NEW.movimiento_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_bloquear_cerrado_entrada ON detalle_entrada")
    op.execute(
        """
        CREATE TRIGGER trg_bloquear_cerrado_entrada
            BEFORE INSERT ON detalle_entrada
            FOR EACH ROW
            EXECUTE FUNCTION bloquear_detalle_si_movimiento_cerrado()
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_bloquear_cerrado_salida ON detalle_salida")
    op.execute(
        """
        CREATE TRIGGER trg_bloquear_cerrado_salida
            BEFORE INSERT ON detalle_salida
            FOR EACH ROW
            EXECUTE FUNCTION bloquear_detalle_si_movimiento_cerrado()
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pacas (
            id                SERIAL PRIMARY KEY,
            codigo            VARCHAR(30) NOT NULL UNIQUE,
            material_id       INTEGER NOT NULL REFERENCES materiales(id),
            en_inventario     BOOLEAN NOT NULL DEFAULT true,
            fecha_registro    TIMESTAMPTZ NOT NULL DEFAULT now(),
            detalle_salida_id INTEGER REFERENCES detalle_salida(id),
            CHECK (
                (en_inventario = true  AND detalle_salida_id IS NULL)
                OR
                (en_inventario = false AND detalle_salida_id IS NOT NULL)
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS inventario (
            material_id     INTEGER PRIMARY KEY REFERENCES materiales(id),
            peso_total      NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (peso_total >= 0),
            actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS inventario_pacas (
            material_id     INTEGER PRIMARY KEY REFERENCES materiales(id),
            cantidad        INTEGER NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
            actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sincronizar_inventario_entrada()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO inventario (material_id, peso_total, actualizado_en)
            VALUES (NEW.material_id, NEW.peso_neto, now())
            ON CONFLICT (material_id) DO UPDATE
                SET peso_total = inventario.peso_total + NEW.peso_neto,
                    actualizado_en = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_entrada ON detalle_entrada")
    op.execute(
        """
        CREATE TRIGGER trg_sincronizar_inventario_entrada
            AFTER INSERT ON detalle_entrada
            FOR EACH ROW
            EXECUTE FUNCTION sincronizar_inventario_entrada()
        """
    )
    op.execute(
        """
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
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_pacas_alta ON pacas")
    op.execute(
        """
        CREATE TRIGGER trg_sincronizar_inventario_pacas_alta
            AFTER INSERT ON pacas
            FOR EACH ROW
            EXECUTE FUNCTION sincronizar_inventario_pacas_alta()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sincronizar_inventario_pacas_baja()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE inventario_pacas
                SET cantidad = cantidad - 1,
                    actualizado_en = now()
                WHERE material_id = NEW.material_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_pacas_baja ON pacas")
    op.execute(
        """
        CREATE TRIGGER trg_sincronizar_inventario_pacas_baja
            AFTER UPDATE OF en_inventario ON pacas
            FOR EACH ROW
            WHEN (OLD.en_inventario = true AND NEW.en_inventario = false)
            EXECUTE FUNCTION sincronizar_inventario_pacas_baja()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_pacas_baja ON pacas")
    op.execute("DROP FUNCTION IF EXISTS sincronizar_inventario_pacas_baja CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_pacas_alta ON pacas")
    op.execute("DROP FUNCTION IF EXISTS sincronizar_inventario_pacas_alta CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_entrada ON detalle_entrada")
    op.execute("DROP FUNCTION IF EXISTS sincronizar_inventario_entrada CASCADE")
    op.execute("DROP TABLE IF EXISTS inventario_pacas CASCADE")
    op.execute("DROP TABLE IF EXISTS inventario CASCADE")
    op.execute("DROP TABLE IF EXISTS pacas CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_bloquear_cerrado_salida ON detalle_salida")
    op.execute("DROP TRIGGER IF EXISTS trg_bloquear_cerrado_entrada ON detalle_entrada")
    op.execute("DROP FUNCTION IF EXISTS bloquear_detalle_si_movimiento_cerrado CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_completar_precio_compra ON detalle_entrada")
    op.execute("DROP FUNCTION IF EXISTS completar_precio_compra CASCADE")
    op.execute("DROP TABLE IF EXISTS detalle_salida CASCADE")
    op.execute("DROP TABLE IF EXISTS detalle_entrada CASCADE")
    op.execute("DROP TABLE IF EXISTS movimientos CASCADE")
    op.execute("DROP TABLE IF EXISTS clientes CASCADE")
    op.execute("DROP TABLE IF EXISTS proveedores CASCADE")
