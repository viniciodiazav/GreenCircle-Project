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
tickets/schema.sql
tickets/triggers.sql
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

**Regla de negocio (agregada 2026-07-26): un movimiento no puede mezclar
proveedores o clientes.** Todos los `detalle_entrada` de un mismo
`movimiento_id` deben tener el mismo `proveedor_id`, y todos los
`detalle_salida` de un mismo `movimiento_id` deben tener el mismo
`cliente_id`. `movimientos/triggers.sql` lo bloquea (`RAISE EXCEPTION`) al
insertar un detalle que no coincide con el proveedor/cliente ya usado en ese
movimiento; el backend valida lo mismo antes para dar un 409 legible.

**`monto_total`** (en `detalle_entrada`/`detalle_salida`, `movimientos/schema.sql`):
a diferencia de `peso_neto`/`precio_compra`, NO se calcula solo -- lo ingresa
quien registra el detalle, debe ser `>= 0`.

**Un movimiento sin detalles no puede cerrarse.** `movimientos/triggers.sql`
lo bloquea (`RAISE EXCEPTION`) en un `BEFORE UPDATE OF cerrado`: no habría de
dónde sacar el proveedor/cliente ni los materiales para su ticket.

**`tickets`** (`tickets/schema.sql` + `tickets/triggers.sql`): al cerrar un
movimiento se genera automáticamente su comprobante -- `ticket_venta` si es
`SALIDA`, `ticket_compra` si es `ENTRADA` -- vía trigger `AFTER UPDATE OF
cerrado ON movimientos` (mismo principio que los historiales: el backend
nunca escribe en estas tablas). Cliente/proveedor y materiales se sacan de
los detalles del movimiento (por la regla de arriba, todos comparten el
mismo proveedor/cliente). El `folio` es único y se arma solo:
`{V|C}-{fecha YYYYMMDD}-{correlativo del día}` (mismo patrón que el código
de pacas). `tickets/schema.sql` requiere `movimientos` (con
`detalle_entrada`/`detalle_salida`), `pacas`, `materiales`, `proveedores` y
`clientes` ya creados.

**Edición y cancelación de detalles (agregado 2026-07-26).** Antes, un error
de captura no tenía forma de corregirse salvo con `ajustes_inventario`
(que corrige el número final, no el registro original). Ahora, mientras el
movimiento sigue **abierto**, el backend permite:
- Editar `peso_bruto`/`tara`/`descuento` (y otros campos sin efecto lateral)
  de un `detalle_entrada`. `peso_neto` se recalcula solo (columna
  `GENERATED`) y `trg_sincronizar_inventario_entrada_editada`
  (`inventario/triggers.sql`) aplica el **delta** (`peso_neto` nuevo menos
  el viejo) al inventario, anotando la corrección en `historial_kg` --
  mismo principio que un ajuste manual, pero automático.
- Cancelar (borrar) un `detalle_entrada`: `trg_revertir_inventario_entrada_cancelada`
  resta de vuelta su `peso_neto` del inventario. Si ese material ya se
  compactó en una paca y revertir dejaría `peso_total` negativo, el `CHECK`
  de siempre rechaza la cancelación (409 legible desde el backend).
- Cancelar (borrar) un `detalle_salida`: `trg_liberar_pacas_al_cancelar_detalle_salida`
  (`movimientos/triggers.sql`) libera las pacas que vendía
  (`en_inventario = true`, `detalle_salida_id = NULL`) antes del `DELETE`,
  lo que dispara en cadena `trg_reactivar_inventario_pacas`
  (`inventario/triggers.sql`, +1 a `inventario_pacas`) y
  `trg_historial_paca_cancelacion` (`pacas/triggers.sql`, evento
  `CANCELACION` en `historial_pacas` -- nunca se borra el evento `VENTA`
  original).
- Cancelar (borrar) un movimiento **vacío y abierto** (sin detalles).

**No se permite editar/cancelar nada una vez el movimiento está cerrado**
-- ya se generó su ticket y ya se disparó todo el efecto en cadena
(inventario, historial, pacas vendidas); revertir eso de forma segura queda
fuera de este alcance. Tampoco se permite cambiar `proveedor_id`/`material_id`/
`cliente_id`/`pacas` vía edición -- si la entidad o las pacas están mal, se
cancela la línea y se crea una nueva.

**Autenticación (agregado 2026-07-26): `admin` único → `usuarios` (varios,
sin roles).** Decisión explícita del usuario: no quiere admin/operador,
solo cuentas independientes con los mismos permisos -- la idea es saber
*quién* hizo qué, no restringir *qué puede hacer* cada quien. `activo`
permite dar de baja una cuenta sin borrarla (y sin romper los FKs de abajo).

**Trazabilidad de creado_por / usuario_id.** `movimientos`, `detalle_entrada`,
`detalle_salida` y `ajustes_inventario` tienen `creado_por` (FK a
`usuarios`), llenado por el backend al crear -- nullable porque los
registros previos a esta migración no tienen autor conocido.

Para las **cancelaciones** (que hacen `DELETE`, no `UPDATE`), no hay fila
que lleve un `cancelado_por` -- lo que existe es el rastro que ya dejaban
los triggers en `historial_kg`/`historial_pacas`. Se les agregó `usuario_id`
(nullable, mismo motivo) y los dos triggers de cancelación
(`revertir_inventario_entrada_cancelada`, `registrar_historial_paca_cancelacion`)
lo leen de `current_setting('app.usuario_actual', true)` -- un trigger de
Postgres no recibe parámetros del backend, así que la app hace
`SET LOCAL app.usuario_actual = '<id>'` justo antes del `DELETE` (misma
transacción, se resetea solo al terminar). Ver `app.core.database.
set_usuario_actual` del lado del backend. Los demás triggers que insertan en
`historial_kg` (entrada normal, paca registrada, ajuste) no cambiaron -- ahí
`usuario_id` queda `NULL`, solo se llena en la cancelación.

## Cómo agregar un módulo nuevo (ej. `camiones`)

1. Crear `base-datos/camiones/` con `schema.sql` (+ `triggers.sql`/`seed.sql` si aplica).
2. Generar la migración de Alembic correspondiente en `backend/alembic/versions/` como statements `op.execute(...)` que reflejen ese `schema.sql`/`triggers.sql` (igual que la migración inicial `bb0b4a94fa9f`). **Nunca reescribir migraciones ya aplicadas.**
3. Añadir el import del `models.py` nuevo (`backend/app/modules/camiones/models.py`) en `backend/alembic/env.py` para que Alembic detecte su metadata.
4. Actualizar el orden de aplicación de este README si hay dependencias de FK entre módulos.

Ver también `backend/README.md` para la convención del lado del código (routers/services/models).
