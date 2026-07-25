-- Dominio inventario: proyecciones de stock, sincronizadas por triggers en
-- triggers.sql. No son fuente de verdad -- movimientos/detalle_entrada y
-- pacas lo son -- son una vista materializada a mano para lectura rápida.

-- Material suelto acumulado por lo recibido en detalle_entrada.
-- NOTA: todavía no existe la lógica de "una paca consume material suelto al
-- compactarse", así que por ahora este total solo crece con entradas.
CREATE TABLE IF NOT EXISTS inventario (
    material_id     INTEGER PRIMARY KEY REFERENCES materiales(id),
    peso_total      NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (peso_total >= 0),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Pacas actualmente en bodega (en_inventario = true), agrupadas por material.
CREATE TABLE IF NOT EXISTS inventario_pacas (
    material_id     INTEGER PRIMARY KEY REFERENCES materiales(id),
    cantidad        INTEGER NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    actualizado_en  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Historial de cambios al inventario de material suelto (mismo patrón que
-- historial_precios: log append-only, lo llena un trigger, nunca el backend).
CREATE TABLE IF NOT EXISTS historial_kg (
    id              SERIAL PRIMARY KEY,
    material_id     INTEGER NOT NULL REFERENCES materiales(id),
    peso_anterior   NUMERIC(12, 2) NOT NULL,
    peso_nuevo      NUMERIC(12, 2) NOT NULL,
    fecha_cambio    TIMESTAMPTZ NOT NULL DEFAULT now()
);
