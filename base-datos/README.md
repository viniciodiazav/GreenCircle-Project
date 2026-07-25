# Base de datos — convención de módulos

Un folder por dominio, mismos tres nombres de archivo siempre (los que apliquen):

- `schema.sql` — tablas del dominio.
- `triggers.sql` — funciones/triggers del dominio (si aplica).
- `seed.sql` — datos iniciales (si aplica).

## Orden de aplicación actual

```
materiales/schema.sql
materiales/triggers.sql
auth/schema.sql
proveedores/schema.sql
clientes/schema.sql
movimientos/schema.sql
movimientos/triggers.sql
pacas/schema.sql
pacas/triggers.sql
inventario/schema.sql
inventario/triggers.sql
materiales/seed.sql
auth/seed.sql
```

`movimientos/schema.sql` requiere que `materiales`, `proveedores` y `clientes`
ya existan (FKs de `detalle_entrada`/`detalle_salida`). `pacas/schema.sql`
requiere `materiales` y `detalle_salida` (de `movimientos`); `pacas/triggers.sql`
además crea `historial_pacas`, que también referencia `detalle_salida`.
`inventario/` requiere `materiales`, `detalle_entrada` y `pacas`; su
`schema.sql` incluye `historial_kg` y su `triggers.sql` lo llena desde el
mismo trigger que sincroniza `inventario`.

**Regla de negocio: un detalle no puede referenciar una entidad inactiva.**
`movimientos/triggers.sql` bloquea (`RAISE EXCEPTION`) insertar un
`detalle_entrada` con `proveedor_id`/`material_id` de un registro con
`activo = false`, o un `detalle_salida` con `cliente_id` inactivo.
`pacas/triggers.sql` hace lo mismo para `material_id` al registrar una paca.
Por eso este orden importa: las columnas `activo` de `proveedores`,
`clientes` y `materiales` deben existir antes de aplicar estos triggers
(ya lo hacen, están en el `schema.sql` de cada uno).

**`ajustes_inventario`** (en `inventario/schema.sql`): ledger de correcciones
manuales al inventario suelto (merma, conteo físico, error de báscula).
`peso_ajuste` es un delta (+/-), nunca un valor absoluto. Registrar una paca
también resta su `peso` del inventario suelto del material (trigger en
`inventario/triggers.sql`) -- ambos casos, junto con las entradas, quedan
anotados en `historial_kg`.

**Gotcha de Postgres: `INSERT ... ON CONFLICT DO UPDATE` no sirve para
deltas que pueden ser negativos.** Postgres valida los `CHECK` contra el
valor propuesto del `INSERT` **antes** de detectar el conflicto -- así que
`INSERT INTO inventario (material_id, peso_total) VALUES (1, -5) ON
CONFLICT (material_id) DO UPDATE SET peso_total = inventario.peso_total - 5`
falla el `CHECK (peso_total >= 0)` aunque el resultado final del `UPDATE`
sí sea válido (ej. 10 - 5 = 5). La solución: `UPDATE` explícito primero, y
si `NOT FOUND` recién ahí el `INSERT` (ver `sincronizar_inventario_paca_registrada`
y `sincronizar_inventario_ajuste` en `inventario/triggers.sql`). Los
triggers que solo suman (`sincronizar_inventario_entrada`,
`sincronizar_inventario_pacas_alta`) no tienen este problema porque su
valor inicial de `INSERT` siempre es válido por sí solo.

## Cómo agregar un módulo nuevo (ej. `camiones`)

1. Crear `base-datos/camiones/` con `schema.sql` (+ `triggers.sql`/`seed.sql` si aplica).
2. Generar la migración de Alembic correspondiente en `backend/alembic/versions/` como statements `op.execute(...)` que reflejen ese `schema.sql`/`triggers.sql` (igual que la migración inicial `bb0b4a94fa9f`). **Nunca reescribir migraciones ya aplicadas.**
3. Añadir el import del `models.py` nuevo (`backend/app/modules/camiones/models.py`) en `backend/alembic/env.py` para que Alembic detecte su metadata.
4. Actualizar el orden de aplicación de este README si hay dependencias de FK entre módulos.

Ver también `backend/README.md` para la convención del lado del código (routers/services/models).
