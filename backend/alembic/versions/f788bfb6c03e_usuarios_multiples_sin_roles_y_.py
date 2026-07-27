"""usuarios múltiples (sin roles) y trazabilidad de creado_por/usuario_id

Revision ID: f788bfb6c03e
Revises: 811b7bea892e
Create Date: 2026-07-26 20:53:31.865958

Mirrors base-datos/{auth,movimientos,inventario,pacas}/{schema,triggers}.sql
(fuente canónica y legible).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f788bfb6c03e'
down_revision: Union[str, None] = '811b7bea892e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- auth: admin único -> usuarios (varios, sin roles) --
    op.execute("ALTER TABLE admin RENAME TO usuarios")
    op.execute("ALTER TABLE usuarios ADD COLUMN activo BOOLEAN NOT NULL DEFAULT true")

    # -- creado_por: quién registró cada movimiento/detalle/ajuste --
    op.execute("ALTER TABLE movimientos ADD COLUMN creado_por INTEGER REFERENCES usuarios(id)")
    op.execute("ALTER TABLE detalle_entrada ADD COLUMN creado_por INTEGER REFERENCES usuarios(id)")
    op.execute("ALTER TABLE detalle_salida ADD COLUMN creado_por INTEGER REFERENCES usuarios(id)")
    op.execute("ALTER TABLE ajustes_inventario ADD COLUMN creado_por INTEGER REFERENCES usuarios(id)")

    # -- usuario_id: quién canceló, en las tablas de historial que ya
    # existían para estos eventos --
    op.execute("ALTER TABLE historial_kg ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id)")
    op.execute("ALTER TABLE historial_pacas ADD COLUMN usuario_id INTEGER REFERENCES usuarios(id)")

    # -- revertir_inventario_entrada_cancelada: ahora anota quién canceló,
    # leyendo el SET LOCAL que hace el backend antes del DELETE --
    op.execute(
        """
        CREATE OR REPLACE FUNCTION revertir_inventario_entrada_cancelada()
        RETURNS TRIGGER AS $$
        DECLARE
            peso_previo NUMERIC(12, 2);
            usuario_actual INTEGER;
        BEGIN
            SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = OLD.material_id;
            peso_previo := COALESCE(peso_previo, 0);
            usuario_actual := NULLIF(current_setting('app.usuario_actual', true), '')::INTEGER;

            UPDATE inventario
                SET peso_total = peso_total - OLD.peso_neto,
                    actualizado_en = now()
                WHERE material_id = OLD.material_id;

            INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio, usuario_id)
            VALUES (OLD.material_id, peso_previo, peso_previo - OLD.peso_neto, now(), usuario_actual);

            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    # -- registrar_historial_paca_cancelacion: mismo principio --
    op.execute(
        """
        CREATE OR REPLACE FUNCTION registrar_historial_paca_cancelacion()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO historial_pacas (paca_id, evento, detalle_salida_id, fecha, usuario_id)
            VALUES (
                NEW.id, 'CANCELACION', OLD.detalle_salida_id, now(),
                NULLIF(current_setting('app.usuario_actual', true), '')::INTEGER
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION registrar_historial_paca_cancelacion()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO historial_pacas (paca_id, evento, detalle_salida_id, fecha)
            VALUES (NEW.id, 'CANCELACION', OLD.detalle_salida_id, now());
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION revertir_inventario_entrada_cancelada()
        RETURNS TRIGGER AS $$
        DECLARE
            peso_previo NUMERIC(12, 2);
        BEGIN
            SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = OLD.material_id;
            peso_previo := COALESCE(peso_previo, 0);

            UPDATE inventario
                SET peso_total = peso_total - OLD.peso_neto,
                    actualizado_en = now()
                WHERE material_id = OLD.material_id;

            INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio)
            VALUES (OLD.material_id, peso_previo, peso_previo - OLD.peso_neto, now());

            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute("ALTER TABLE historial_pacas DROP COLUMN usuario_id")
    op.execute("ALTER TABLE historial_kg DROP COLUMN usuario_id")

    op.execute("ALTER TABLE ajustes_inventario DROP COLUMN creado_por")
    op.execute("ALTER TABLE detalle_salida DROP COLUMN creado_por")
    op.execute("ALTER TABLE detalle_entrada DROP COLUMN creado_por")
    op.execute("ALTER TABLE movimientos DROP COLUMN creado_por")

    op.execute("ALTER TABLE usuarios DROP COLUMN activo")
    op.execute("ALTER TABLE usuarios RENAME TO admin")
