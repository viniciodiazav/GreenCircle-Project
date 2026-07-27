# Backend — Centro de Recolección

FastAPI + SQLAlchemy async (asyncpg) + Alembic + PostgreSQL.

## Arquitectura

```
app/
├── main.py
├── core/              # transversal: config, database, security (JWT). Lo usan todos los módulos.
└── modules/
    ├── auth/          # models.py, schemas.py, service.py, router.py
    ├── materiales/
    ├── proveedores/
    ├── clientes/
    ├── movimientos/       # SOLO la cabecera (crear/listar/cerrar)
    ├── detalle_entrada/   # líneas de ENTRADA, módulo separado
    ├── detalle_salida/    # líneas de SALIDA, módulo separado
    ├── pacas/
    ├── inventario/        # solo lectura (proyección)
    ├── historial_precios/ # solo lectura, antes vivía anidado en materiales
    ├── historial_kg/      # solo lectura
    ├── historial_pacas/   # solo lectura
    ├── ajustes_inventario/ # correcciones manuales de inventario (merma, conteo físico)
    ├── tickets_venta/      # solo lectura, autogenerado al cerrar un movimiento SALIDA
    └── tickets_compra/     # solo lectura, autogenerado al cerrar un movimiento ENTRADA
```

Cada módulo es un paquete autocontenido por dominio (no por tipo de archivo). El `router.py` solo define rutas HTTP y delega; toda la lógica de negocio vive en `service.py` (funciones pequeñas, una responsabilidad, reciben `db: AsyncSession` explícito, sin `Depends`). Los modelos importan `Base` desde `app.core.database`. Un módulo no importa modelos/servicios internos de otro módulo — si necesitan compartir algo, ese algo sube a `core`.

`movimientos`, `detalle_entrada`, `detalle_salida` y `pacas` quedaron deliberadamente separados aunque están muy acoplados por negocio (cada línea de detalle pertenece a un movimiento; vender pacas las liga a un detalle_salida) — la idea es que cada uno sea un recurso HTTP independiente, con su propio router y su propia URL base (`/detalle-entrada`, `/detalle-salida`, no anidados bajo `/movimientos/{id}/...`), no solo archivos separados que en el fondo siguen siendo una sola API. `movimiento_id` va en el body (`POST`) o como query param (`GET ?movimiento_id=`), igual que `proveedor_id`/`material_id`/etc. Los cruces de import que sí existen:
- `detalle_entrada/service.py` y `detalle_salida/service.py` importan `Movimiento` y `validar_movimiento_para_detalle(...)` de `movimientos/service.py` (evita duplicar la validación de tipo/cerrado en los dos).
- `detalle_salida/service.py` importa `Paca` de `pacas/models.py`: vender pacas es, en una sola transacción, crear el `detalle_salida` y marcar esas pacas como vendidas — partirlo en dos módulos sin este import dejaría estados a medias posibles (paca "vendida" sin venta real, o viceversa).
- `historial_pacas/service.py` importa `Paca` de `pacas/models.py` únicamente para poder filtrar por `material_id` (join). `historial_precios` e `historial_kg` no importan de nadie.
- `pacas/service.py` importa `Inventario` de `inventario/models.py`: registrar una paca resta su peso del inventario suelto (ver abajo), así que hay que confirmar que haya suficiente antes de intentarlo.
- `ajustes_inventario/service.py` importa `Material` de `materiales/models.py` solo para validar que `material_id` exista (mismo patrón que otros módulos).

**Los tres módulos de historial (`historial_precios`, `historial_kg`, `historial_pacas`) son de solo lectura y 100% independientes entre sí y de los módulos que auditan** (`materiales`, `inventario`, `pacas`) — cada uno es su propio router top-level (`/historial-precios`, `/historial-kg`, `/historial-pacas`), no anidado bajo el recurso que audita. Los tres se llenan solos vía trigger de Postgres (nunca el backend escribe en ellos): `historial_precios` cuando cambia `materiales.precio_actual`, `historial_kg` cuando entra material por `detalle_entrada`, `historial_pacas` cuando una paca se registra (evento `ALTA`) o se vende (evento `VENTA`, ligado a su `detalle_salida_id`).

**Autenticación (agregada 2026-07-26, JWT):** todos los endpoints requieren `Authorization: Bearer <token>` excepto `POST /auth/login` y `GET /materiales` (el listado público de precios que usa la app móvil sin login, ver `app-movil/src/screens/HomeScreen.tsx`). Se aplica a nivel de router con `dependencies=[Depends(get_current_user)]` (`app.core.security`); `materiales` es el único módulo mixto, así que protege sus rutas de admin una por una en vez de a nivel de router.

**Roles (agregado 2026-07-27, revierte "sin roles" del mismo 26):** `usuarios.rol` es `operador` (default) o `administrador`, viaja como claim `rol` en el JWT. `Depends(require_admin)` (`app.core.security`) rechaza con 403 si el rol no es `administrador` — se usa además de (no en vez de) `get_current_user` en los endpoints admin-only. Todo lo que no está listado abajo es común a ambos roles (ver, crear/editar/cerrar/cancelar movimientos, detalles y pacas):
- `POST`/`PATCH /materiales` (crear, precio, activo)
- `POST`/`PATCH /proveedores` y `/clientes` (crear, activo)
- `POST /ajustes-inventario`
- Todo `/usuarios` (ni siquiera `GET` es visible para un operador)

**Rate limiting de login (agregado 2026-07-26):** 5 intentos fallidos por `usuario` en 15 minutos → `429 Too Many Requests`. Vive en un `dict` a nivel de módulo (`app/modules/auth/service.py`) -- no sobrevive un reinicio del proceso ni se comparte entre workers si algún día se corre con más de uno; suficiente para el volumen actual, pero si se escala a múltiples procesos habría que moverlo a Redis o a una tabla.

**Sin logout real (decisión explícita, 2026-07-26):** cerrar sesión en el cliente solo borra el token guardado localmente -- el JWT sigue siendo válido hasta que expira solo (`JWT_EXPIRE_MINUTES`, 8h por defecto). Se evaluó una blacklist de tokens revocados (`jti` + tabla + query en cada request) y se descartó por ahora: es complejidad que no hace falta a este tamaño de proyecto: 8h fijas es un riesgo aceptable.

**Gestión de usuarios (agregado 2026-07-26, `/usuarios`, exclusivo de administrador):**
- `GET /usuarios`, `GET /usuarios/{id}` — sin `password_hash` en la respuesta, incluye `rol`.
- `POST /usuarios` — `{"usuario", "password", "rol"?}` (`password` mínimo 8 caracteres, 422 si no; `rol` opcional, default `"operador"`). 409 si `usuario` ya existe.
- `PATCH /usuarios/{id}` — `{"activo": false}`, `{"password": "..."}` y/o `{"rol": "administrador"}`, al menos uno de los tres (400 si ninguno). No hay `DELETE` -- dar de baja es `activo: false`, igual que proveedores/clientes/materiales.

### Cómo agregar un módulo nuevo (ej. `camiones`)

1. Crear `app/modules/<nombre>/` con `__init__.py`, `models.py`, `schemas.py`, `service.py`, `router.py`.
2. `models.py` importa `Base` desde `app.core.database`.
3. `service.py` contiene la lógica de negocio; `router.py` solo orquesta HTTP (`Depends(get_db)`, `Depends(get_current_user)` desde `app.core`, normalmente a nivel de router con `dependencies=[...]`) y llama al service.
4. Registrar el router en `app/main.py` (`app.include_router(...)`).
5. Del lado SQL, ver `../base-datos/README.md`.

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # editar DATABASE_URL y JWT_SECRET
```

### Con Docker (agregado 2026-07-26)

Alternativa al setup manual de arriba -- levanta Postgres y el backend juntos:

```bash
docker compose up --build
```

El `Dockerfile` corre `alembic upgrade head` antes de `uvicorn` en cada arranque, así que las tablas quedan listas solas. El seed del admin sigue siendo manual (ver el comentario en `../docker-compose.yml` con el comando exacto) -- las migraciones crean estructura, no insertan datos, mismo principio que el setup sin Docker.

## Base de datos

La base y el rol de Postgres deben existir de antemano.

```bash
./venv/bin/alembic upgrade head
```

Esto aplica todas las migraciones, incluidas las de `proveedores`/`clientes`/`movimientos`/`pacas`/`inventario` y la de `historial_kg`/`historial_pacas`, que mirrorean `../base-datos/{ese-dominio}/*.sql` (ver `../base-datos/README.md` para la fuente legible).

Si prefieres aplicar los `.sql` directo (sin Alembic) en un entorno nuevo, respeta el orden de `../base-datos/README.md`.

## Levantar el servidor

```bash
./venv/bin/uvicorn app.main:app --reload --port 8000
```

### Logging (agregado 2026-07-26)

Configurado en `app/core/logging_config.py`, llamado al importar `app.main`. Va a dos lados a la vez:
- Consola (stdout) -- se ve en vivo en la terminal o con `docker compose logs`.
- Archivo rotativo `backend/logs/app.log` (5MB por archivo, 3 de respaldo) -- no se versiona (`.gitignore`), sobrevive a cerrar la terminal.

Alcance actual, deliberadamente acotado a lo sensible a seguridad y a errores no controlados (no cada request de negocio, eso sería mucho ruido para lo que aporta hoy):
- Login exitoso/fallido y bloqueos por rate-limit (`app/modules/auth/service.py`).
- Alta de usuario, activar/desactivar, cambio de password -- incluye quién lo hizo (`actor`), no solo sobre quién.
- Cualquier excepción no controlada (500) vía `app.exception_handler(Exception)` en `main.py` -- antes de esto, un 500 solo dejaba rastro mientras la terminal seguía abierta.

## Endpoints

- `GET /materiales` — solo materiales activos, y solo `{"nombre", "precio"}` (nada más).
- `GET /materiales/admin` — todos los materiales (activos e inactivos) con toda la información.
- `GET /materiales/admin/activos` — solo los activos, con toda la información.
- `POST /materiales` — Body: `{"nombre", "unidad", "precio_actual"}`. `nombre` debe ser único (409 si ya existe), `precio_actual` debe ser > 0 (422 si no). El `codigo` se genera solo (ver abajo).
- `PATCH /materiales/{id}` — Body opcional: `{"precio_actual": 2.50}` y/o `{"activo": false}` (al menos uno de los dos; `activo=false` es el soft delete, no borra el registro ni su historial). `nombre`/`codigo`/`unidad` no son editables tras crear el material.
- `POST /auth/login` — único mecanismo de auth del repo (`{"usuario": "...", "password": "..."}` → `{"access_token", "token_type": "bearer"}`). 401 si el usuario no existe, la contraseña no coincide, o la cuenta tiene `activo = false`.

Nota: el historial de precios ya NO está aquí, se movió a `/historial-precios` (ver abajo) — `materiales` es solo materiales.

**Proveedores / clientes** (mismo shape, requiere auth):
- `GET /proveedores`, `GET /proveedores?activo=true`, `GET /proveedores?activo=false` — sin el query param trae todos (activos e inactivos).
- `POST /proveedores` (`{"nombre", "direccion"?, "contacto"?}`) — nace siempre `activo: true`.
- `GET /proveedores/{id}`.
- `PATCH /proveedores/{id}` (cualquier subconjunto de `nombre`/`direccion`/`contacto`/`activo`) — `activo: false` es el soft delete, no borra el registro (necesario porque `detalle_entrada`/`detalle_salida` ya pueden tener FKs apuntando a él).
- Igual para `/clientes`.

**Movimientos** (solo cabecera, requiere auth):
- `POST /movimientos` — `{"tipo": "ENTRADA"|"SALIDA", "descripcion"?}`.
- `GET /movimientos`, `GET /movimientos?tipo=ENTRADA`, `GET /movimientos/{id}`.
- `PATCH /movimientos/{id}` (agregado 2026-07-26) — edita solo `descripcion`. Permitido siempre, abierto o cerrado (no tiene efecto lateral).
- `PATCH /movimientos/{id}/cerrar` — cierra el movimiento (409 si ya estaba cerrado). Un movimiento cerrado ya no acepta nuevos detalles (409, aplicado también en la BD vía trigger). **409 si el movimiento no tiene ningún detalle** (ver regla abajo) — al cerrar con éxito se genera automáticamente su ticket (ver `/tickets-venta`/`/tickets-compra` abajo).
- `DELETE /movimientos/{id}` (agregado 2026-07-26) — cancela un movimiento **vacío y abierto** (creado por error, sin detalles todavía). 409 si ya está cerrado, 409 si ya tiene detalles (cancélalos primero, uno por uno, con `DELETE /detalle-entrada/{id}` o `/detalle-salida/{id}`).

**Detalle de entrada** (router y recurso propios, `/detalle-entrada`, requiere auth):
- `POST /detalle-entrada` — `{"movimiento_id", "proveedor_id", "material_id", "peso_bruto", "tara", "monto_total", "descuento"?, "descripcion"?, "descripcion_descuento"?}`. 409 si el movimiento no es ENTRADA o ya está cerrado; 400 si `proveedor_id`/`material_id` no existen; **409 si el proveedor o el material están inactivos** (`activo = false`); 400 si `peso_bruto <= tara`; 422 si `descuento` no está entre 0 y 100; **409 si el movimiento ya tiene detalles de otro proveedor** (ver regla abajo). `descuento` es opcional (default 0, porcentaje). `peso_neto` y `precio_compra` (snapshot del precio de compra vigente) se calculan solos: `peso_neto = (peso_bruto - tara) * (1 - descuento / 100)` — el descuento se aplica sobre el neto ya calculado, no sobre el bruto (ej. merma por humedad/impurezas detectada al pesar). `descripcion_descuento` es libre, para anotar el motivo. `monto_total` (agregado 2026-07-26) es **obligatorio** y **no se calcula solo** — lo ingresa quien registra la entrada, debe ser `>= 0` (422 si falta o es negativo).
- `GET /detalle-entrada`, `GET /detalle-entrada?movimiento_id=...`, `GET /detalle-entrada/{id}`.
- `PATCH /detalle-entrada/{id}` (agregado 2026-07-26) — corrige `peso_bruto`/`tara`/`descuento`/`monto_total`/`descripcion`/`descripcion_descuento` de una línea mal capturada. **`proveedor_id`/`material_id`/`movimiento_id` NO son editables** (si esos están mal, cancela la línea y crea una nueva). Solo mientras el movimiento sigue **abierto** (409 si cerrado). `peso_neto` se recalcula solo y un trigger en BD aplica el **delta** (nuevo menos viejo) al inventario, dejando la corrección anotada en `historial-kg` — mismo principio que un ajuste manual, pero automático. 400 si el nuevo `peso_bruto`/`tara` viola `peso_bruto > tara`. 409 si la corrección dejaría el inventario de ese material en negativo (ya se compactó una paca con ese material desde que se registró la entrada).
- `DELETE /detalle-entrada/{id}` (agregado 2026-07-26) — cancela (borra) una línea mal capturada. Solo mientras el movimiento sigue abierto (409 si cerrado). Un trigger en BD revierte lo que había sumado al inventario, anotándolo en `historial-kg`. **409 si el inventario de ese material ya se usó** (ej. ya se compactó una paca) y revertir lo dejaría en negativo — en ese caso hay que corregir con `ajustes_inventario` en vez de cancelar.

**Detalle de salida** (router y recurso propios, `/detalle-salida`, requiere auth):
- `POST /detalle-salida` — `{"movimiento_id", "cliente_id", "precio_venta", "monto_total", "pacas": [id, id, ...], "descripcion"?}`. Esto vende esas pacas específicas: 409 si el movimiento no es SALIDA o ya está cerrado, 400 si `cliente_id` no existe, **409 si el cliente está inactivo**, 404 si alguna paca no existe, 409 si alguna ya estaba vendida, **409 si el movimiento ya tiene detalles de otro cliente** (ver regla abajo). `cantidad_pacas` en la respuesta es derivado (cuenta pacas ligadas), no una columna. `monto_total` (agregado 2026-07-26) es **obligatorio**, `>= 0`, no se calcula solo.
- `GET /detalle-salida`, `GET /detalle-salida?movimiento_id=...`, `GET /detalle-salida/{id}`.
- `PATCH /detalle-salida/{id}` (agregado 2026-07-26) — corrige `precio_venta`/`monto_total`/`descripcion`. **`cliente_id`/`pacas` NO son editables** (si el cliente está mal o hay que cambiar qué pacas se vendieron, cancela la línea y crea una nueva). Solo mientras el movimiento sigue abierto (409 si cerrado). Sin efecto lateral (no toca pacas ni inventario).
- `DELETE /detalle-salida/{id}` (agregado 2026-07-26) — cancela (borra) una venta mal capturada. Solo mientras el movimiento sigue abierto (409 si cerrado). Un trigger en BD libera las pacas vendidas (`en_inventario = true`, `detalle_salida_id = NULL`), lo que reactiva `inventario_pacas` y anota un evento `CANCELACION` en `historial-pacas` (nunca borra el evento `VENTA` original).

**Nota general de ediciones/cancelaciones:** ninguna se permite una vez el movimiento está **cerrado** — ya se generó su ticket y ya se disparó todo el efecto en cadena (inventario, historial, pacas vendidas); revertir eso de forma segura queda fuera de este alcance. Si te equivocaste después de cerrar, usa `ajustes_inventario` para corregir el inventario.

**Regla de negocio (agregada 2026-07-26): un movimiento no puede mezclar proveedores/clientes.** Todos los `detalle_entrada` de un mismo movimiento deben ser del mismo `proveedor_id`; todos los `detalle_salida` de un mismo movimiento deben ser del mismo `cliente_id`. Doble capa: trigger en BD (`base-datos/movimientos/triggers.sql`) + validación en el service (409 legible). Es lo que permite que el ticket generado al cerrar el movimiento tenga un único proveedor/cliente.

**Regla de negocio (agregada 2026-07-26): un movimiento sin detalles no puede cerrarse.** Mismo principio doble-capa. Existe porque el ticket que se genera al cerrar necesita de dónde sacar el proveedor/cliente y los materiales.

**Pacas** (requiere auth):
- `GET /pacas`, `GET /pacas?en_inventario=true`, `GET /pacas/{id}`.
- `POST /pacas` — `{"material_id", "peso"}`. **`codigo` NO se manda** — lo arma un trigger de Postgres: `{codigo_material}-{fecha YYYYMMDD}-{correlativo del día para ese material}` (ej. `CART-20260725-01`, `CART-20260725-02`). `peso` es aproximado o real, no se distingue a nivel de esquema (solo debe ser > 0). Nace siempre `en_inventario: true`. 400 si `material_id` no existe, 422 si `peso <= 0`, 409 si el material está inactivo, **409 si no hay suficiente inventario suelto de ese material** (ver abajo). **Registrar una paca resta su `peso` del inventario suelto** (`inventario.peso_total`) del material — se asume que ese material ya se compactó y dejó de estar "suelto".

**Regla de negocio (agregada 2026-07-25): ningún detalle/paca puede referenciar una entidad inactiva.** Validado en dos capas: la BD lo garantiza siempre (trigger `BEFORE INSERT`, ver `base-datos/{movimientos,pacas}/triggers.sql` — imposible saltárselo ni con un INSERT directo), y el backend valida antes para devolver un 409 con mensaje legible en vez de dejar burbujear la excepción cruda de Postgres.

**Inventario** (solo lectura, requiere auth):
- `GET /inventario` — material suelto acumulado por `material_id` (`peso_total`).
- `GET /inventario/pacas` — pacas actualmente en bodega por `material_id` (`cantidad`).

**Ajustes de inventario** (agregado 2026-07-25, router propio `/ajustes-inventario`, requiere auth): corrige discrepancias entre lo que dice la BD y un conteo físico real (merma por humedad, error de báscula, robo, etc.) — sin esto, `inventario.peso_total` solo puede crecer (entradas) o bajar por pacas registradas, nunca por una corrección manual.
- `POST /ajustes-inventario` — `{"material_id", "peso_ajuste", "motivo", "comentarios"?}`. `peso_ajuste` es un **delta** (no un valor absoluto): negativo resta (merma), positivo suma (se encontró más de lo esperado). `motivo` es obligatorio (422 si viene vacío o falta), `comentarios` es libre y opcional. 400 si `material_id` no existe, 422 si `peso_ajuste == 0`, 409 si el ajuste dejaría `peso_total` en negativo.
- `GET /ajustes-inventario`, `GET /ajustes-inventario?material_id=...`.
- Cada ajuste también queda anotado en `/historial-kg` (mismo `peso_anterior`/`peso_nuevo` que un `detalle_entrada`) — una sola línea de tiempo con entradas, pacas y ajustes juntos.

**Historiales** (los tres solo lectura, requiere auth, routers independientes):
- `GET /historial-precios`, `GET /historial-precios?material_id=...` — cada cambio de `precio_actual` (`precio_anterior`, `precio_nuevo`, `fecha_cambio`).
- `GET /historial-kg`, `GET /historial-kg?material_id=...` — cada cambio al inventario de material suelto (`peso_anterior`, `peso_nuevo`, `fecha_cambio`): entradas (suma), pacas registradas (resta) y ajustes manuales (+/-), todos en la misma línea de tiempo.
- `GET /historial-pacas`, `GET /historial-pacas?paca_id=...`, `GET /historial-pacas?material_id=...` — eventos de cada paca: `evento` (`ALTA`, `VENTA` o `CANCELACION` -- este último agregado 2026-07-26, cuando se cancela el `detalle_salida` que la vendió), `detalle_salida_id` (en `VENTA`; `null` en `CANCELACION`, porque el `detalle_salida` que canceló ya no existe), `fecha`.

**Tickets de venta / compra** (agregado 2026-07-26, solo lectura, requiere auth, routers independientes): comprobantes que se generan solos al cerrar un movimiento — el backend nunca escribe en estas tablas (mismo principio que los historiales). Al cerrar un movimiento `SALIDA` se crea un `ticket_venta`; al cerrar uno `ENTRADA`, un `ticket_compra`. Cliente/proveedor y materiales se sacan de los detalles del movimiento (nombre, no id) — por la regla de "un solo proveedor/cliente por movimiento" todos comparten el mismo. `fecha` es la fecha de cierre del movimiento. `folio` es único, formato `{V|C}-{YYYYMMDD}-{correlativo del día}` (mismo patrón que el código de pacas).
- `GET /tickets-venta`, `GET /tickets-venta?movimiento_id=...`, `GET /tickets-venta/{id}` — `{"movimiento_id", "folio", "cliente", "cantidad_pacas", "materiales": [...], "fecha"}`. `cantidad_pacas` es el total de pacas vendidas en ese movimiento; `materiales` son los nombres distintos de los materiales de esas pacas.
- `GET /tickets-compra`, `GET /tickets-compra?movimiento_id=...`, `GET /tickets-compra/{id}` — `{"movimiento_id", "folio", "proveedor", "materiales": [...], "fecha"}`. `materiales` son los nombres distintos de los materiales comprados en ese movimiento.

### Paginación (agregada 2026-07-26)

Todos los `GET` que devuelven listas (`/materiales`, `/materiales/admin`, `/materiales/admin/activos`, `/proveedores`, `/clientes`, `/movimientos`, `/detalle-entrada`, `/detalle-salida`, `/pacas`, `/inventario`, `/inventario/pacas`, `/historial-precios`, `/historial-kg`, `/historial-pacas`, `/ajustes-inventario`, `/tickets-venta`, `/tickets-compra`, `/usuarios`) aceptan `?limit=` (default 50, máximo 200, 422 si es menor a 1 o mayor a 200) y `?offset=` (default 0, 422 si es negativo), y devuelven un sobre en vez de un array plano:

```json
{"items": [...], "total": 123, "limit": 50, "offset": 0}
```

`total` es el conteo total de filas que cumplen los filtros (sin `limit`/`offset`) — así un cliente puede calcular cuántas páginas hay (`ceil(total / limit)`) sin tener que traerse todo. **Este es un cambio de forma de respuesta**: antes estos endpoints devolvían `[...]` directo: cualquier cliente existente (incluida la app móvil, cuando exista) tiene que leer `data.items` en vez de `data`.

### Generación automática del código

Se genera a partir del `nombre` (sin acentos, mayúsculas), en `app/modules/materiales/codigo.py`:
- Una palabra: sus primeras 4 letras (si tiene menos de 4, se completa con `0` a la derecha). Ej. "Vidrio" → `VIDR`, "Oro" → `ORO0`.
- Varias palabras: primeras 4 letras de la primera palabra + `-` + primeras 3 letras de la segunda. Ej. "Plástico PET" → `PLAS-PET`.
- Si el código generado ya existe, se le agrega `-2`, `-3`, ... hasta encontrar uno libre.

## Probar manualmente

Interfaz interactiva: levanta el servidor y abre `http://localhost:8000/docs`.

Por curl:

```bash
curl http://localhost:8000/materiales
# -> 200, sin token (es el único GET público, ver nota de auth arriba)

TOKEN=$(curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario": "admin", "password": "GreenCircle2026i++"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -X PATCH http://localhost:8000/materiales/1 \
  -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" \
  -d '{"precio_actual": 2.00}'

curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/historial-precios?material_id=1
```

Los tres historiales se llenan solos (vía triggers de Postgres, `base-datos/{materiales,inventario,pacas}/triggers.sql`), nunca por lógica del backend.

## Tests

```bash
./venv/bin/pip install -r requirements-dev.txt   # pytest, pytest-asyncio, httpx (no van en requirements.txt de producción)
./venv/bin/pytest -v
```

Corren contra **tu base de datos real** (`DATABASE_URL` del `.env`), no contra una base separada ni contra sqlite -- necesario porque las reglas de negocio viven en triggers/constraints de Postgres (columnas `GENERATED`, `CHECK`, `RAISE EXCEPTION`), que sqlite no puede reproducir. Aun así **no dejan ningún dato**: cada test corre dentro de una transacción que se revierte al terminar (`tests/conftest.py`, fixture `db_session` con `join_transaction_mode="create_savepoint"` -- el mismo patrón documentado en los docs de SQLAlchemy para probar apps con sesión-por-request). El endpoint completo se prueba de verdad vía HTTP (`httpx.AsyncClient` + `ASGITransport`, sin levantar un servidor real), inyectando esa sesión con `app.dependency_overrides`.

Cobertura actual: `materiales` (código, precio, historial, activo), `auth` (login, rate-limiting tras 5 intentos fallidos, cuenta inactiva no loguea), `usuarios` (crear, duplicado, activar/desactivar, cambio de password, 400 sin campos), `proveedores`/`clientes` (CRUD, activo), el flujo completo de `movimientos`/`detalle_entrada`/`detalle_salida`/`pacas`/`inventario`/historiales (incluye las reglas de negocio: tipo de movimiento correcto, movimiento cerrado, pacas ya vendidas, FKs inválidas, `monto_total` obligatorio y `>= 0`, mismo proveedor/cliente por movimiento, movimiento sin detalles no cierra, autogeneración y contenido de `tickets_venta`/`tickets_compra`, unicidad de folio), edición/cancelación de movimientos y detalles (`tests/test_correcciones.py`: delta de inventario al editar, reversión al cancelar, liberación de pacas, bloqueo cuando el movimiento está cerrado o el inventario ya se usó), paginación (`tests/test_paginacion.py`: forma de la respuesta, límites, offsets, el caso con join de `detalle-salida`), protección de endpoints (`tests/test_proteccion_endpoints.py`: 401 sin token, `GET /materiales` público, 200 con token), lecturas básicas de cada módulo (`tests/test_lecturas_basicas.py`: 404 por id inexistente, listados sin filtro) que el resto de la suite no ejercita por estar enfocada en flujos de negocio, y permisos por rol (`tests/test_roles.py`: operador recibe 403 en cada endpoint admin-only, sí puede el flujo diario completo incluida la cancelación, rol default `operador` al crear, admin puede cambiar el rol de otro usuario).
