"""detalle_entrada: agrega descuento y descripcion_descuento

Revision ID: 07c40b8ab4e6
Revises: caa6c1c94b7d
Create Date: 2026-07-25 17:21:41.678649

Mirrors base-datos/movimientos/schema.sql (fuente canónica y legible).
peso_neto es GENERATED ALWAYS -- Postgres no permite alterar la expresión de
una columna generada in-place, hay que tirarla y recrearla.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '07c40b8ab4e6'
down_revision: Union[str, None] = 'caa6c1c94b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE detalle_entrada ADD COLUMN descuento NUMERIC(5, 2) NOT NULL DEFAULT 0 "
        "CHECK (descuento >= 0 AND descuento <= 100)"
    )
    op.execute("ALTER TABLE detalle_entrada ADD COLUMN descripcion_descuento TEXT")
    op.execute("ALTER TABLE detalle_entrada DROP COLUMN peso_neto")
    op.execute(
        "ALTER TABLE detalle_entrada ADD COLUMN peso_neto NUMERIC(10, 2) "
        "GENERATED ALWAYS AS ((peso_bruto - tara) * (1 - descuento / 100)) STORED"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE detalle_entrada DROP COLUMN peso_neto")
    op.execute(
        "ALTER TABLE detalle_entrada ADD COLUMN peso_neto NUMERIC(10, 2) "
        "GENERATED ALWAYS AS (peso_bruto - tara) STORED"
    )
    op.execute("ALTER TABLE detalle_entrada DROP COLUMN descripcion_descuento")
    op.execute("ALTER TABLE detalle_entrada DROP COLUMN descuento")
