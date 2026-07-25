"""proveedores y clientes: soft delete con activo

Revision ID: c736c93e361b
Revises: 7a32f2073b21
Create Date: 2026-07-25 16:39:33.443104

Mirrors base-datos/{proveedores,clientes}/schema.sql (fuente canónica y
legible).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c736c93e361b'
down_revision: Union[str, None] = '7a32f2073b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE proveedores ADD COLUMN activo BOOLEAN NOT NULL DEFAULT true")
    op.execute("ALTER TABLE clientes ADD COLUMN activo BOOLEAN NOT NULL DEFAULT true")


def downgrade() -> None:
    op.execute("ALTER TABLE clientes DROP COLUMN activo")
    op.execute("ALTER TABLE proveedores DROP COLUMN activo")
