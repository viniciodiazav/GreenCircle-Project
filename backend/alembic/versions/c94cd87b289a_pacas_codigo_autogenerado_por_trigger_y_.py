"""pacas: codigo autogenerado por trigger y agrega peso

Revision ID: c94cd87b289a
Revises: 07c40b8ab4e6
Create Date: 2026-07-25 17:36:15.993109

Mirrors base-datos/pacas/{schema,triggers}.sql (fuente canónica y legible).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c94cd87b289a'
down_revision: Union[str, None] = '07c40b8ab4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE pacas ADD COLUMN peso NUMERIC(10, 2) NOT NULL CHECK (peso > 0)")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION generar_codigo_paca()
        RETURNS TRIGGER AS $$
        DECLARE
            codigo_mat  VARCHAR(30);
            correlativo INTEGER;
        BEGIN
            SELECT codigo INTO codigo_mat FROM materiales WHERE id = NEW.material_id;

            SELECT count(*) + 1 INTO correlativo
            FROM pacas
            WHERE material_id = NEW.material_id
              AND fecha_registro::date = CURRENT_DATE;

            NEW.codigo := codigo_mat || '-' || to_char(now(), 'YYYYMMDD') || '-' || lpad(correlativo::text, 2, '0');

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_generar_codigo_paca ON pacas")
    op.execute(
        """
        CREATE TRIGGER trg_generar_codigo_paca
            BEFORE INSERT ON pacas
            FOR EACH ROW
            EXECUTE FUNCTION generar_codigo_paca()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_generar_codigo_paca ON pacas")
    op.execute("DROP FUNCTION IF EXISTS generar_codigo_paca CASCADE")
    op.execute("ALTER TABLE pacas DROP COLUMN peso")
