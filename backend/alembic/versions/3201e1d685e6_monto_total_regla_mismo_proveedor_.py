"""monto_total, regla mismo proveedor cliente, tickets venta compra

Revision ID: 3201e1d685e6
Revises: 575e1eb19191
Create Date: 2026-07-25 23:48:57.608898

Mirrors base-datos/movimientos/{schema,triggers}.sql y base-datos/tickets/
{schema,triggers}.sql (fuente canónica y legible).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3201e1d685e6'
down_revision: Union[str, None] = '575e1eb19191'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- monto_total en detalle_entrada / detalle_salida --
    op.execute(
        "ALTER TABLE detalle_entrada ADD COLUMN monto_total NUMERIC(10, 2) NOT NULL "
        "CHECK (monto_total >= 0)"
    )
    op.execute(
        "ALTER TABLE detalle_salida ADD COLUMN monto_total NUMERIC(10, 2) NOT NULL "
        "CHECK (monto_total >= 0)"
    )

    # -- regla: un movimiento no puede mezclar proveedores/clientes --
    op.execute(
        """
        CREATE OR REPLACE FUNCTION validar_mismo_proveedor_detalle_entrada()
        RETURNS TRIGGER AS $$
        DECLARE
            proveedor_existente INTEGER;
        BEGIN
            SELECT proveedor_id INTO proveedor_existente
            FROM detalle_entrada
            WHERE movimiento_id = NEW.movimiento_id
            LIMIT 1;

            IF proveedor_existente IS NOT NULL AND proveedor_existente <> NEW.proveedor_id THEN
                RAISE EXCEPTION 'El movimiento % ya tiene detalles del proveedor %, no puede mezclar proveedores', NEW.movimiento_id, proveedor_existente;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_validar_mismo_proveedor_entrada ON detalle_entrada")
    op.execute(
        """
        CREATE TRIGGER trg_validar_mismo_proveedor_entrada
            BEFORE INSERT ON detalle_entrada
            FOR EACH ROW
            EXECUTE FUNCTION validar_mismo_proveedor_detalle_entrada()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION validar_mismo_cliente_detalle_salida()
        RETURNS TRIGGER AS $$
        DECLARE
            cliente_existente INTEGER;
        BEGIN
            SELECT cliente_id INTO cliente_existente
            FROM detalle_salida
            WHERE movimiento_id = NEW.movimiento_id
            LIMIT 1;

            IF cliente_existente IS NOT NULL AND cliente_existente <> NEW.cliente_id THEN
                RAISE EXCEPTION 'El movimiento % ya tiene detalles del cliente %, no puede mezclar clientes', NEW.movimiento_id, cliente_existente;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_validar_mismo_cliente_salida ON detalle_salida")
    op.execute(
        """
        CREATE TRIGGER trg_validar_mismo_cliente_salida
            BEFORE INSERT ON detalle_salida
            FOR EACH ROW
            EXECUTE FUNCTION validar_mismo_cliente_detalle_salida()
        """
    )

    # -- regla: un movimiento sin detalles no puede cerrarse --
    op.execute(
        """
        CREATE OR REPLACE FUNCTION validar_movimiento_no_vacio()
        RETURNS TRIGGER AS $$
        DECLARE
            tiene_detalles BOOLEAN;
        BEGIN
            IF NEW.cerrado = true AND OLD.cerrado = false THEN
                IF NEW.tipo = 'ENTRADA' THEN
                    SELECT EXISTS(SELECT 1 FROM detalle_entrada WHERE movimiento_id = NEW.id) INTO tiene_detalles;
                ELSE
                    SELECT EXISTS(SELECT 1 FROM detalle_salida WHERE movimiento_id = NEW.id) INTO tiene_detalles;
                END IF;

                IF NOT tiene_detalles THEN
                    RAISE EXCEPTION 'El movimiento % no tiene detalles, no se puede cerrar', NEW.id;
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_validar_movimiento_no_vacio ON movimientos")
    op.execute(
        """
        CREATE TRIGGER trg_validar_movimiento_no_vacio
            BEFORE UPDATE OF cerrado ON movimientos
            FOR EACH ROW
            EXECUTE FUNCTION validar_movimiento_no_vacio()
        """
    )

    # -- dominio tickets --
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ticket_venta (
            id             SERIAL PRIMARY KEY,
            movimiento_id  INTEGER NOT NULL UNIQUE REFERENCES movimientos(id),
            folio          VARCHAR(30) NOT NULL UNIQUE,
            cliente        TEXT NOT NULL,
            cantidad_pacas INTEGER NOT NULL,
            materiales     TEXT[] NOT NULL,
            fecha          TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ticket_compra (
            id             SERIAL PRIMARY KEY,
            movimiento_id  INTEGER NOT NULL UNIQUE REFERENCES movimientos(id),
            folio          VARCHAR(30) NOT NULL UNIQUE,
            proveedor      TEXT NOT NULL,
            materiales     TEXT[] NOT NULL,
            fecha          TIMESTAMPTZ NOT NULL
        )
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION generar_folio_ticket_venta()
        RETURNS TRIGGER AS $$
        DECLARE
            correlativo INTEGER;
        BEGIN
            SELECT count(*) + 1 INTO correlativo
            FROM ticket_venta
            WHERE fecha::date = NEW.fecha::date;

            NEW.folio := 'V-' || to_char(NEW.fecha, 'YYYYMMDD') || '-' || lpad(correlativo::text, 2, '0');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_generar_folio_ticket_venta ON ticket_venta")
    op.execute(
        """
        CREATE TRIGGER trg_generar_folio_ticket_venta
            BEFORE INSERT ON ticket_venta
            FOR EACH ROW
            EXECUTE FUNCTION generar_folio_ticket_venta()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION generar_folio_ticket_compra()
        RETURNS TRIGGER AS $$
        DECLARE
            correlativo INTEGER;
        BEGIN
            SELECT count(*) + 1 INTO correlativo
            FROM ticket_compra
            WHERE fecha::date = NEW.fecha::date;

            NEW.folio := 'C-' || to_char(NEW.fecha, 'YYYYMMDD') || '-' || lpad(correlativo::text, 2, '0');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_generar_folio_ticket_compra ON ticket_compra")
    op.execute(
        """
        CREATE TRIGGER trg_generar_folio_ticket_compra
            BEFORE INSERT ON ticket_compra
            FOR EACH ROW
            EXECUTE FUNCTION generar_folio_ticket_compra()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION generar_ticket_al_cerrar_movimiento()
        RETURNS TRIGGER AS $$
        DECLARE
            cliente_nombre    TEXT;
            proveedor_nombre  TEXT;
            lista_materiales  TEXT[];
            total_pacas       INTEGER;
        BEGIN
            IF NEW.cerrado = true AND OLD.cerrado = false THEN
                IF NEW.tipo = 'SALIDA' THEN
                    SELECT c.nombre INTO cliente_nombre
                    FROM detalle_salida ds
                    JOIN clientes c ON c.id = ds.cliente_id
                    WHERE ds.movimiento_id = NEW.id
                    LIMIT 1;

                    SELECT array_agg(DISTINCT m.nombre) INTO lista_materiales
                    FROM pacas p
                    JOIN detalle_salida ds ON ds.id = p.detalle_salida_id
                    JOIN materiales m ON m.id = p.material_id
                    WHERE ds.movimiento_id = NEW.id;

                    SELECT count(*) INTO total_pacas
                    FROM pacas p
                    JOIN detalle_salida ds ON ds.id = p.detalle_salida_id
                    WHERE ds.movimiento_id = NEW.id;

                    INSERT INTO ticket_venta (movimiento_id, cliente, cantidad_pacas, materiales, fecha)
                    VALUES (NEW.id, cliente_nombre, total_pacas, COALESCE(lista_materiales, ARRAY[]::TEXT[]), now());

                ELSIF NEW.tipo = 'ENTRADA' THEN
                    SELECT pr.nombre INTO proveedor_nombre
                    FROM detalle_entrada de
                    JOIN proveedores pr ON pr.id = de.proveedor_id
                    WHERE de.movimiento_id = NEW.id
                    LIMIT 1;

                    SELECT array_agg(DISTINCT m.nombre) INTO lista_materiales
                    FROM detalle_entrada de
                    JOIN materiales m ON m.id = de.material_id
                    WHERE de.movimiento_id = NEW.id;

                    INSERT INTO ticket_compra (movimiento_id, proveedor, materiales, fecha)
                    VALUES (NEW.id, proveedor_nombre, COALESCE(lista_materiales, ARRAY[]::TEXT[]), now());
                END IF;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_generar_ticket_al_cerrar ON movimientos")
    op.execute(
        """
        CREATE TRIGGER trg_generar_ticket_al_cerrar
            AFTER UPDATE OF cerrado ON movimientos
            FOR EACH ROW
            EXECUTE FUNCTION generar_ticket_al_cerrar_movimiento()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_generar_ticket_al_cerrar ON movimientos")
    op.execute("DROP FUNCTION IF EXISTS generar_ticket_al_cerrar_movimiento CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_generar_folio_ticket_compra ON ticket_compra")
    op.execute("DROP FUNCTION IF EXISTS generar_folio_ticket_compra CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_generar_folio_ticket_venta ON ticket_venta")
    op.execute("DROP FUNCTION IF EXISTS generar_folio_ticket_venta CASCADE")
    op.execute("DROP TABLE IF EXISTS ticket_compra")
    op.execute("DROP TABLE IF EXISTS ticket_venta")

    op.execute("DROP TRIGGER IF EXISTS trg_validar_movimiento_no_vacio ON movimientos")
    op.execute("DROP FUNCTION IF EXISTS validar_movimiento_no_vacio CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_validar_mismo_cliente_salida ON detalle_salida")
    op.execute("DROP FUNCTION IF EXISTS validar_mismo_cliente_detalle_salida CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_validar_mismo_proveedor_entrada ON detalle_entrada")
    op.execute("DROP FUNCTION IF EXISTS validar_mismo_proveedor_detalle_entrada CASCADE")

    op.execute("ALTER TABLE detalle_salida DROP COLUMN monto_total")
    op.execute("ALTER TABLE detalle_entrada DROP COLUMN monto_total")
