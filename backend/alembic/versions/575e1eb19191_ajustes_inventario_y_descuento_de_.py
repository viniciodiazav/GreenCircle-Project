"""ajustes_inventario y descuento de inventario al registrar paca

Revision ID: 575e1eb19191
Revises: c94cd87b289a
Create Date: 2026-07-25 17:50:35.263096

Mirrors base-datos/inventario/{schema,triggers}.sql (fuente canónica y
legible).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '575e1eb19191'
down_revision: Union[str, None] = 'c94cd87b289a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ajustes_inventario (
            id           SERIAL PRIMARY KEY,
            material_id  INTEGER NOT NULL REFERENCES materiales(id),
            peso_ajuste  NUMERIC(12, 2) NOT NULL CHECK (peso_ajuste <> 0),
            motivo       TEXT NOT NULL,
            comentarios  TEXT,
            fecha        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sincronizar_inventario_paca_registrada()
        RETURNS TRIGGER AS $$
        DECLARE
            peso_previo NUMERIC(12, 2);
        BEGIN
            SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = NEW.material_id;
            peso_previo := COALESCE(peso_previo, 0);

            UPDATE inventario
                SET peso_total = peso_total - NEW.peso,
                    actualizado_en = now()
                WHERE material_id = NEW.material_id;

            IF NOT FOUND THEN
                INSERT INTO inventario (material_id, peso_total, actualizado_en)
                VALUES (NEW.material_id, -NEW.peso, now());
            END IF;

            INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio)
            VALUES (NEW.material_id, peso_previo, peso_previo - NEW.peso, now());

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_paca_registrada ON pacas")
    op.execute(
        """
        CREATE TRIGGER trg_sincronizar_inventario_paca_registrada
            AFTER INSERT ON pacas
            FOR EACH ROW
            EXECUTE FUNCTION sincronizar_inventario_paca_registrada()
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sincronizar_inventario_ajuste()
        RETURNS TRIGGER AS $$
        DECLARE
            peso_previo NUMERIC(12, 2);
        BEGIN
            SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = NEW.material_id;
            peso_previo := COALESCE(peso_previo, 0);

            UPDATE inventario
                SET peso_total = peso_total + NEW.peso_ajuste,
                    actualizado_en = now()
                WHERE material_id = NEW.material_id;

            IF NOT FOUND THEN
                INSERT INTO inventario (material_id, peso_total, actualizado_en)
                VALUES (NEW.material_id, NEW.peso_ajuste, now());
            END IF;

            INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio)
            VALUES (NEW.material_id, peso_previo, peso_previo + NEW.peso_ajuste, now());

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_ajuste ON ajustes_inventario")
    op.execute(
        """
        CREATE TRIGGER trg_sincronizar_inventario_ajuste
            AFTER INSERT ON ajustes_inventario
            FOR EACH ROW
            EXECUTE FUNCTION sincronizar_inventario_ajuste()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_ajuste ON ajustes_inventario")
    op.execute("DROP FUNCTION IF EXISTS sincronizar_inventario_ajuste CASCADE")
    op.execute("DROP TABLE IF EXISTS ajustes_inventario CASCADE")
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_paca_registrada ON pacas")
    op.execute("DROP FUNCTION IF EXISTS sincronizar_inventario_paca_registrada CASCADE")
