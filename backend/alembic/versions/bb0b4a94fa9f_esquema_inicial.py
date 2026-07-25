"""esquema inicial: materiales, historial_precios, admin + trigger de auditoría

Revision ID: bb0b4a94fa9f
Revises:
Create Date: 2026-07-22

Mirrors base-datos/schema.sql y base-datos/triggers.sql (fuente canónica y
legible de la BD). Se repite aquí como statements separados porque el driver
asyncpg no admite múltiples comandos en un solo execute.
"""

from alembic import op

revision = "bb0b4a94fa9f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS materiales (
            id              SERIAL PRIMARY KEY,
            nombre          VARCHAR(100) NOT NULL UNIQUE,
            unidad          VARCHAR(20) NOT NULL DEFAULT 'kg',
            precio_actual   NUMERIC(10, 2) NOT NULL CHECK (precio_actual >= 0),
            actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS historial_precios (
            id              SERIAL PRIMARY KEY,
            material_id     INTEGER NOT NULL REFERENCES materiales(id) ON DELETE CASCADE,
            precio_anterior NUMERIC(10, 2) NOT NULL,
            precio_nuevo    NUMERIC(10, 2) NOT NULL,
            fecha_cambio    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS admin (
            id              SERIAL PRIMARY KEY,
            usuario         VARCHAR(50) NOT NULL UNIQUE,
            password_hash   VARCHAR(255) NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION registrar_cambio_precio()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.precio_actual IS DISTINCT FROM OLD.precio_actual THEN
                INSERT INTO historial_precios (material_id, precio_anterior, precio_nuevo, fecha_cambio)
                VALUES (OLD.id, OLD.precio_actual, NEW.precio_actual, now());

                NEW.actualizado_en := now();
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_registrar_cambio_precio ON materiales")
    op.execute(
        """
        CREATE TRIGGER trg_registrar_cambio_precio
            BEFORE UPDATE OF precio_actual ON materiales
            FOR EACH ROW
            EXECUTE FUNCTION registrar_cambio_precio()
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS historial_precios CASCADE")
    op.execute("DROP TABLE IF EXISTS materiales CASCADE")
    op.execute("DROP TABLE IF EXISTS admin CASCADE")
    op.execute("DROP FUNCTION IF EXISTS registrar_cambio_precio CASCADE")
