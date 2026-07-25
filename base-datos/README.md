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

## Cómo agregar un módulo nuevo (ej. `camiones`)

1. Crear `base-datos/camiones/` con `schema.sql` (+ `triggers.sql`/`seed.sql` si aplica).
2. Generar la migración de Alembic correspondiente en `backend/alembic/versions/` como statements `op.execute(...)` que reflejen ese `schema.sql`/`triggers.sql` (igual que la migración inicial `bb0b4a94fa9f`). **Nunca reescribir migraciones ya aplicadas.**
3. Añadir el import del `models.py` nuevo (`backend/app/modules/camiones/models.py`) en `backend/alembic/env.py` para que Alembic detecte su metadata.
4. Actualizar el orden de aplicación de este README si hay dependencias de FK entre módulos.

Ver también `backend/README.md` para la convención del lado del código (routers/services/models).
