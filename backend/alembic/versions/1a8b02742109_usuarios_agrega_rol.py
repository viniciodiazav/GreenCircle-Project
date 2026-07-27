"""usuarios: agrega rol (operador/administrador)

Revision ID: 1a8b02742109
Revises: f788bfb6c03e
Create Date: 2026-07-27 01:20:53.440401

Mirrors base-datos/auth/schema.sql (fuente canónica y legible).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1a8b02742109'
down_revision: Union[str, None] = 'f788bfb6c03e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE usuarios ADD COLUMN rol VARCHAR(20) NOT NULL DEFAULT 'operador' "
        "CHECK (rol IN ('operador', 'administrador'))"
    )
    # El admin sembrado en auth/seed.sql es el único que sabemos que debe ser
    # administrador -- todo lo demás (incluidos usuarios creados en pruebas)
    # se queda en el default 'operador'.
    op.execute("UPDATE usuarios SET rol = 'administrador' WHERE usuario = 'admin'")


def downgrade() -> None:
    op.execute("ALTER TABLE usuarios DROP COLUMN rol")
