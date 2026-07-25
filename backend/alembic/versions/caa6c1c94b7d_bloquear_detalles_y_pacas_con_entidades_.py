"""bloquear detalles y pacas con entidades inactivas

Revision ID: caa6c1c94b7d
Revises: c736c93e361b
Create Date: 2026-07-25 17:05:44.100249

Mirrors base-datos/{movimientos,pacas}/triggers.sql (fuente canónica y
legible).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'caa6c1c94b7d'
down_revision: Union[str, None] = 'c736c93e361b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION validar_activos_detalle_entrada()
        RETURNS TRIGGER AS $$
        DECLARE
            proveedor_activo BOOLEAN;
            material_activo  BOOLEAN;
        BEGIN
            SELECT activo INTO proveedor_activo FROM proveedores WHERE id = NEW.proveedor_id;
            IF NOT proveedor_activo THEN
                RAISE EXCEPTION 'El proveedor % está inactivo', NEW.proveedor_id;
            END IF;

            SELECT activo INTO material_activo FROM materiales WHERE id = NEW.material_id;
            IF NOT material_activo THEN
                RAISE EXCEPTION 'El material % está inactivo', NEW.material_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_validar_activos_entrada ON detalle_entrada")
    op.execute(
        """
        CREATE TRIGGER trg_validar_activos_entrada
            BEFORE INSERT ON detalle_entrada
            FOR EACH ROW
            EXECUTE FUNCTION validar_activos_detalle_entrada()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION validar_activo_detalle_salida()
        RETURNS TRIGGER AS $$
        DECLARE
            cliente_activo BOOLEAN;
        BEGIN
            SELECT activo INTO cliente_activo FROM clientes WHERE id = NEW.cliente_id;
            IF NOT cliente_activo THEN
                RAISE EXCEPTION 'El cliente % está inactivo', NEW.cliente_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_validar_activo_salida ON detalle_salida")
    op.execute(
        """
        CREATE TRIGGER trg_validar_activo_salida
            BEFORE INSERT ON detalle_salida
            FOR EACH ROW
            EXECUTE FUNCTION validar_activo_detalle_salida()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION validar_material_activo_paca()
        RETURNS TRIGGER AS $$
        DECLARE
            material_activo BOOLEAN;
        BEGIN
            SELECT activo INTO material_activo FROM materiales WHERE id = NEW.material_id;
            IF NOT material_activo THEN
                RAISE EXCEPTION 'El material % está inactivo', NEW.material_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_validar_material_activo_paca ON pacas")
    op.execute(
        """
        CREATE TRIGGER trg_validar_material_activo_paca
            BEFORE INSERT ON pacas
            FOR EACH ROW
            EXECUTE FUNCTION validar_material_activo_paca()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_validar_material_activo_paca ON pacas")
    op.execute("DROP FUNCTION IF EXISTS validar_material_activo_paca CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_validar_activo_salida ON detalle_salida")
    op.execute("DROP FUNCTION IF EXISTS validar_activo_detalle_salida CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_validar_activos_entrada ON detalle_entrada")
    op.execute("DROP FUNCTION IF EXISTS validar_activos_detalle_entrada CASCADE")
