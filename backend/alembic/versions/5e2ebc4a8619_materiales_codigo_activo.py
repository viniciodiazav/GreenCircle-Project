"""materiales: agrega codigo (SKU), activo (soft delete) y precio > 0

Revision ID: 5e2ebc4a8619
Revises: bb0b4a94fa9f
Create Date: 2026-07-22
"""

from alembic import op

revision = "5e2ebc4a8619"
down_revision = "bb0b4a94fa9f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE materiales ADD COLUMN codigo VARCHAR(30)")

    op.execute("UPDATE materiales SET codigo = 'CART-001' WHERE nombre = 'Cartón'")
    op.execute("UPDATE materiales SET codigo = 'PET-001' WHERE nombre = 'Plástico PET'")
    op.execute("UPDATE materiales SET codigo = 'VID-001' WHERE nombre = 'Vidrio'")
    op.execute("UPDATE materiales SET codigo = 'ALU-001' WHERE nombre = 'Aluminio'")
    op.execute("UPDATE materiales SET codigo = 'PAP-001' WHERE nombre = 'Papel'")

    op.execute("ALTER TABLE materiales ALTER COLUMN codigo SET NOT NULL")
    op.execute("ALTER TABLE materiales ADD CONSTRAINT materiales_codigo_key UNIQUE (codigo)")

    op.execute("ALTER TABLE materiales ADD COLUMN activo BOOLEAN NOT NULL DEFAULT true")

    op.execute("ALTER TABLE materiales DROP CONSTRAINT materiales_precio_actual_check")
    op.execute(
        "ALTER TABLE materiales ADD CONSTRAINT materiales_precio_actual_check "
        "CHECK (precio_actual > 0)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE materiales DROP CONSTRAINT materiales_precio_actual_check")
    op.execute(
        "ALTER TABLE materiales ADD CONSTRAINT materiales_precio_actual_check "
        "CHECK (precio_actual >= 0)"
    )
    op.execute("ALTER TABLE materiales DROP COLUMN activo")
    op.execute("ALTER TABLE materiales DROP CONSTRAINT materiales_codigo_key")
    op.execute("ALTER TABLE materiales DROP COLUMN codigo")
