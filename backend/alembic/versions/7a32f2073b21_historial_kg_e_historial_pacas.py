"""historial_kg e historial_pacas

Revision ID: 7a32f2073b21
Revises: 541b00529aa6
Create Date: 2026-07-25 14:35:04.534459

Mirrors base-datos/{inventario,pacas}/*.sql (fuente canónica y legible). Se
repite aquí como statements separados porque el driver asyncpg no admite
múltiples comandos en un solo execute.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7a32f2073b21'
down_revision: Union[str, None] = '541b00529aa6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS historial_kg (
            id              SERIAL PRIMARY KEY,
            material_id     INTEGER NOT NULL REFERENCES materiales(id),
            peso_anterior   NUMERIC(12, 2) NOT NULL,
            peso_nuevo      NUMERIC(12, 2) NOT NULL,
            fecha_cambio    TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sincronizar_inventario_entrada()
        RETURNS TRIGGER AS $$
        DECLARE
            peso_previo NUMERIC(12, 2);
        BEGIN
            SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = NEW.material_id;
            peso_previo := COALESCE(peso_previo, 0);

            INSERT INTO inventario (material_id, peso_total, actualizado_en)
            VALUES (NEW.material_id, NEW.peso_neto, now())
            ON CONFLICT (material_id) DO UPDATE
                SET peso_total = inventario.peso_total + NEW.peso_neto,
                    actualizado_en = now();

            INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio)
            VALUES (NEW.material_id, peso_previo, peso_previo + NEW.peso_neto, now());

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS historial_pacas (
            id                SERIAL PRIMARY KEY,
            paca_id           INTEGER NOT NULL REFERENCES pacas(id) ON DELETE CASCADE,
            evento            VARCHAR(10) NOT NULL CHECK (evento IN ('ALTA', 'VENTA')),
            detalle_salida_id INTEGER REFERENCES detalle_salida(id),
            fecha             TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION registrar_historial_paca_alta()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO historial_pacas (paca_id, evento, fecha)
            VALUES (NEW.id, 'ALTA', now());
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_historial_paca_alta ON pacas")
    op.execute(
        """
        CREATE TRIGGER trg_historial_paca_alta
            AFTER INSERT ON pacas
            FOR EACH ROW
            EXECUTE FUNCTION registrar_historial_paca_alta()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION registrar_historial_paca_venta()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO historial_pacas (paca_id, evento, detalle_salida_id, fecha)
            VALUES (NEW.id, 'VENTA', NEW.detalle_salida_id, now());
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_historial_paca_venta ON pacas")
    op.execute(
        """
        CREATE TRIGGER trg_historial_paca_venta
            AFTER UPDATE OF en_inventario ON pacas
            FOR EACH ROW
            WHEN (OLD.en_inventario = true AND NEW.en_inventario = false)
            EXECUTE FUNCTION registrar_historial_paca_venta()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_historial_paca_venta ON pacas")
    op.execute("DROP FUNCTION IF EXISTS registrar_historial_paca_venta CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_historial_paca_alta ON pacas")
    op.execute("DROP FUNCTION IF EXISTS registrar_historial_paca_alta CASCADE")
    op.execute("DROP TABLE IF EXISTS historial_pacas CASCADE")
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
    op.execute("DROP TABLE IF EXISTS historial_kg CASCADE")
