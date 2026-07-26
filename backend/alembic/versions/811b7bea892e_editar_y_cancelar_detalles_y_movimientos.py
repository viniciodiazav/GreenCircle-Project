"""editar y cancelar detalles y movimientos

Revision ID: 811b7bea892e
Revises: 3201e1d685e6
Create Date: 2026-07-26 00:30:25.005431

Mirrors base-datos/{pacas,inventario,movimientos}/{schema,triggers}.sql
(fuente canónica y legible).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '811b7bea892e'
down_revision: Union[str, None] = '3201e1d685e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- historial_pacas: nuevo evento CANCELACION + FK a detalle_salida
    # con ON DELETE SET NULL (para poder borrar el detalle_salida sin
    # perder el historial de sus pacas) --
    op.execute("ALTER TABLE historial_pacas DROP CONSTRAINT historial_pacas_evento_check")
    op.execute("ALTER TABLE historial_pacas ALTER COLUMN evento TYPE VARCHAR(15)")
    op.execute(
        "ALTER TABLE historial_pacas ADD CONSTRAINT historial_pacas_evento_check "
        "CHECK (evento IN ('ALTA', 'VENTA', 'CANCELACION'))"
    )
    op.execute(
        "ALTER TABLE historial_pacas DROP CONSTRAINT historial_pacas_detalle_salida_id_fkey"
    )
    op.execute(
        "ALTER TABLE historial_pacas ADD CONSTRAINT historial_pacas_detalle_salida_id_fkey "
        "FOREIGN KEY (detalle_salida_id) REFERENCES detalle_salida(id) ON DELETE SET NULL"
    )

    # -- pacas: log de cancelación cuando una venta se revierte --
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
    op.execute("DROP TRIGGER IF EXISTS trg_historial_paca_cancelacion ON pacas")
    op.execute(
        """
        CREATE TRIGGER trg_historial_paca_cancelacion
            AFTER UPDATE OF en_inventario ON pacas
            FOR EACH ROW
            WHEN (OLD.en_inventario = false AND NEW.en_inventario = true)
            EXECUTE FUNCTION registrar_historial_paca_cancelacion()
        """
    )

    # -- inventario: edición y cancelación de detalle_entrada --
    op.execute(
        """
        CREATE OR REPLACE FUNCTION sincronizar_inventario_entrada_editada()
        RETURNS TRIGGER AS $$
        DECLARE
            peso_previo NUMERIC(12, 2);
            delta       NUMERIC(12, 2);
        BEGIN
            delta := NEW.peso_neto - OLD.peso_neto;
            IF delta = 0 THEN
                RETURN NEW;
            END IF;

            SELECT peso_total INTO peso_previo FROM inventario WHERE material_id = NEW.material_id;
            peso_previo := COALESCE(peso_previo, 0);

            UPDATE inventario
                SET peso_total = peso_total + delta,
                    actualizado_en = now()
                WHERE material_id = NEW.material_id;

            IF NOT FOUND THEN
                INSERT INTO inventario (material_id, peso_total, actualizado_en)
                VALUES (NEW.material_id, delta, now());
            END IF;

            INSERT INTO historial_kg (material_id, peso_anterior, peso_nuevo, fecha_cambio)
            VALUES (NEW.material_id, peso_previo, peso_previo + delta, now());

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_entrada_editada ON detalle_entrada")
    op.execute(
        """
        CREATE TRIGGER trg_sincronizar_inventario_entrada_editada
            AFTER UPDATE OF peso_bruto, tara, descuento ON detalle_entrada
            FOR EACH ROW
            EXECUTE FUNCTION sincronizar_inventario_entrada_editada()
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
    op.execute("DROP TRIGGER IF EXISTS trg_revertir_inventario_entrada_cancelada ON detalle_entrada")
    op.execute(
        """
        CREATE TRIGGER trg_revertir_inventario_entrada_cancelada
            AFTER DELETE ON detalle_entrada
            FOR EACH ROW
            EXECUTE FUNCTION revertir_inventario_entrada_cancelada()
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION reactivar_inventario_pacas()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE inventario_pacas
                SET cantidad = cantidad + 1,
                    actualizado_en = now()
                WHERE material_id = NEW.material_id;

            IF NOT FOUND THEN
                INSERT INTO inventario_pacas (material_id, cantidad, actualizado_en)
                VALUES (NEW.material_id, 1, now());
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_reactivar_inventario_pacas ON pacas")
    op.execute(
        """
        CREATE TRIGGER trg_reactivar_inventario_pacas
            AFTER UPDATE OF en_inventario ON pacas
            FOR EACH ROW
            WHEN (OLD.en_inventario = false AND NEW.en_inventario = true)
            EXECUTE FUNCTION reactivar_inventario_pacas()
        """
    )

    # -- movimientos: liberar pacas al cancelar un detalle_salida --
    op.execute(
        """
        CREATE OR REPLACE FUNCTION liberar_pacas_al_cancelar_detalle_salida()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE pacas
                SET en_inventario = true,
                    detalle_salida_id = NULL
                WHERE detalle_salida_id = OLD.id;

            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_liberar_pacas_al_cancelar_detalle_salida ON detalle_salida")
    op.execute(
        """
        CREATE TRIGGER trg_liberar_pacas_al_cancelar_detalle_salida
            BEFORE DELETE ON detalle_salida
            FOR EACH ROW
            EXECUTE FUNCTION liberar_pacas_al_cancelar_detalle_salida()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_liberar_pacas_al_cancelar_detalle_salida ON detalle_salida")
    op.execute("DROP FUNCTION IF EXISTS liberar_pacas_al_cancelar_detalle_salida CASCADE")

    op.execute("DROP TRIGGER IF EXISTS trg_reactivar_inventario_pacas ON pacas")
    op.execute("DROP FUNCTION IF EXISTS reactivar_inventario_pacas CASCADE")

    op.execute("DROP TRIGGER IF EXISTS trg_revertir_inventario_entrada_cancelada ON detalle_entrada")
    op.execute("DROP FUNCTION IF EXISTS revertir_inventario_entrada_cancelada CASCADE")

    op.execute("DROP TRIGGER IF EXISTS trg_sincronizar_inventario_entrada_editada ON detalle_entrada")
    op.execute("DROP FUNCTION IF EXISTS sincronizar_inventario_entrada_editada CASCADE")

    op.execute("DROP TRIGGER IF EXISTS trg_historial_paca_cancelacion ON pacas")
    op.execute("DROP FUNCTION IF EXISTS registrar_historial_paca_cancelacion CASCADE")

    op.execute(
        "ALTER TABLE historial_pacas DROP CONSTRAINT historial_pacas_detalle_salida_id_fkey"
    )
    op.execute(
        "ALTER TABLE historial_pacas ADD CONSTRAINT historial_pacas_detalle_salida_id_fkey "
        "FOREIGN KEY (detalle_salida_id) REFERENCES detalle_salida(id)"
    )
    op.execute("ALTER TABLE historial_pacas DROP CONSTRAINT historial_pacas_evento_check")
    op.execute("ALTER TABLE historial_pacas ALTER COLUMN evento TYPE VARCHAR(10)")
    op.execute(
        "ALTER TABLE historial_pacas ADD CONSTRAINT historial_pacas_evento_check "
        "CHECK (evento IN ('ALTA', 'VENTA'))"
    )
