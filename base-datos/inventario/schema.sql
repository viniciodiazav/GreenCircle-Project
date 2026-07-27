-- Dominio inventario: proyecciones de stock, sincronizadas por triggers en
-- triggers.sql. No son fuente de verdad -- movimientos/detalle_entrada y
-- pacas lo son -- son una vista materializada a mano para lectura rápida.

-- Material suelto acumulado por lo recibido en detalle_entrada, menos lo que
-- se ha compactado en pacas (ver triggers.sql) y los ajustes manuales de
-- abajo. CHECK (peso_total >= 0): si un ajuste o una paca dejarían el total
-- en negativo, Postgres rechaza la operación -- no puedes compactar más
-- material del que hay registrado como suelto.
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
-- Une TODOS los cambios en una sola línea de tiempo: entradas, pacas
-- registradas, y ajustes manuales (ver ajustes_inventario más abajo).
-- usuario_id: solo lo llena revertir_inventario_entrada_cancelada (ver
-- triggers.sql) -- quién canceló la entrada. Los demás triggers que
-- insertan aquí (entrada normal, paca registrada, ajuste) no lo tocan,
-- queda NULL.
CREATE TABLE IF NOT EXISTS historial_kg (
    id              SERIAL PRIMARY KEY,
    material_id     INTEGER NOT NULL REFERENCES materiales(id),
    peso_anterior   NUMERIC(12, 2) NOT NULL,
    peso_nuevo      NUMERIC(12, 2) NOT NULL,
    fecha_cambio    TIMESTAMPTZ NOT NULL DEFAULT now(),
    usuario_id      INTEGER REFERENCES usuarios(id)
);

-- Ledger de correcciones manuales al inventario suelto -- para cuando un
-- conteo físico no cuadra con lo que dice la BD (merma, humedad, error de
-- báscula, etc.). Nunca se edita inventario directo: se inserta un ajuste y
-- un trigger corrige el total, dejando rastro de cuándo y por qué cambió.
-- peso_ajuste es un delta (+/-), no un valor absoluto -- negativo resta
-- (merma), positivo suma (se encontró más de lo esperado).
CREATE TABLE IF NOT EXISTS ajustes_inventario (
    id           SERIAL PRIMARY KEY,
    material_id  INTEGER NOT NULL REFERENCES materiales(id),
    peso_ajuste  NUMERIC(12, 2) NOT NULL CHECK (peso_ajuste <> 0),
    motivo       TEXT NOT NULL,
    comentarios  TEXT,
    fecha        TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_por   INTEGER REFERENCES usuarios(id)
);
