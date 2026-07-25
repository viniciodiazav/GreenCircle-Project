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
    └── historial_pacas/   # solo lectura
```

Cada módulo es un paquete autocontenido por dominio (no por tipo de archivo). El `router.py` solo define rutas HTTP y delega; toda la lógica de negocio vive en `service.py` (funciones pequeñas, una responsabilidad, reciben `db: AsyncSession` explícito, sin `Depends`). Los modelos importan `Base` desde `app.core.database`. Un módulo no importa modelos/servicios internos de otro módulo — si necesitan compartir algo, ese algo sube a `core`.

`movimientos`, `detalle_entrada`, `detalle_salida` y `pacas` quedaron deliberadamente separados aunque están muy acoplados por negocio (cada línea de detalle pertenece a un movimiento; vender pacas las liga a un detalle_salida) — la idea es que cada uno sea un recurso HTTP independiente, con su propio router y su propia URL base (`/detalle-entrada`, `/detalle-salida`, no anidados bajo `/movimientos/{id}/...`), no solo archivos separados que en el fondo siguen siendo una sola API. `movimiento_id` va en el body (`POST`) o como query param (`GET ?movimiento_id=`), igual que `proveedor_id`/`material_id`/etc. Los cruces de import que sí existen:
- `detalle_entrada/service.py` y `detalle_salida/service.py` importan `Movimiento` y `validar_movimiento_para_detalle(...)` de `movimientos/service.py` (evita duplicar la validación de tipo/cerrado en los dos).
- `detalle_salida/service.py` importa `Paca` de `pacas/models.py`: vender pacas es, en una sola transacción, crear el `detalle_salida` y marcar esas pacas como vendidas — partirlo en dos módulos sin este import dejaría estados a medias posibles (paca "vendida" sin venta real, o viceversa).
- `historial_pacas/service.py` importa `Paca` de `pacas/models.py` únicamente para poder filtrar por `material_id` (join). `historial_precios` e `historial_kg` no importan de nadie.

**Los tres módulos de historial (`historial_precios`, `historial_kg`, `historial_pacas`) son de solo lectura y 100% independientes entre sí y de los módulos que auditan** (`materiales`, `inventario`, `pacas`) — cada uno es su propio router top-level (`/historial-precios`, `/historial-kg`, `/historial-pacas`), no anidado bajo el recurso que audita. Los tres se llenan solos vía trigger de Postgres (nunca el backend escribe en ellos): `historial_precios` cuando cambia `materiales.precio_actual`, `historial_kg` cuando entra material por `detalle_entrada`, `historial_pacas` cuando una paca se registra (evento `ALTA`) o se vende (evento `VENTA`, ligado a su `detalle_salida_id`).

**Sin autenticación (por ahora, en todo):** incluido `materiales` (antes `POST`/`PATCH` pedían el token de admin de la app móvil, ya no) — decisión explícita del usuario: la app móvil y "el sistema" van a tener esquemas de login distintos y ninguno de los dos existe todavía. Cuando se definan, agregar auth siguiendo el patrón que ya estaba en `materiales` (`Depends(get_current_admin)` en el router, nunca en el service).

### Cómo agregar un módulo nuevo (ej. `camiones`)

1. Crear `app/modules/<nombre>/` con `__init__.py`, `models.py`, `schemas.py`, `service.py`, `router.py`.
2. `models.py` importa `Base` desde `app.core.database`.
3. `service.py` contiene la lógica de negocio; `router.py` solo orquesta HTTP (`Depends(get_db)`, `Depends(get_current_admin)` desde `app.core`) y llama al service.
4. Registrar el router en `app/main.py` (`app.include_router(...)`).
5. Del lado SQL, ver `../base-datos/README.md`.

## Setup

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env   # editar DATABASE_URL y JWT_SECRET
```

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

## Endpoints

- `GET /materiales` — solo materiales activos, y solo `{"nombre", "precio"}` (nada más).
- `GET /materiales/admin` — todos los materiales (activos e inactivos) con toda la información.
- `GET /materiales/admin/activos` — solo los activos, con toda la información.
- `POST /materiales` — Body: `{"nombre", "unidad", "precio_actual"}`. `nombre` debe ser único (409 si ya existe), `precio_actual` debe ser > 0 (422 si no). El `codigo` se genera solo (ver abajo).
- `PATCH /materiales/{id}` — Body opcional: `{"precio_actual": 2.50}` y/o `{"activo": false}` (al menos uno de los dos; `activo=false` es el soft delete, no borra el registro ni su historial). `nombre`/`codigo`/`unidad` no son editables tras crear el material.
- `POST /auth/login` — sigue existiendo y sigue siendo el único mecanismo de auth del repo (`{"usuario": "...", "password": "..."}` → token), pero por ahora ningún endpoint de materiales lo exige.

Nota: el historial de precios ya NO está aquí, se movió a `/historial-precios` (ver abajo) — `materiales` es solo materiales.

**Proveedores / clientes** (mismo shape, sin auth por ahora):
- `GET /proveedores`, `GET /proveedores?activo=true`, `GET /proveedores?activo=false` — sin el query param trae todos (activos e inactivos).
- `POST /proveedores` (`{"nombre", "direccion"?, "contacto"?}`) — nace siempre `activo: true`.
- `GET /proveedores/{id}`.
- `PATCH /proveedores/{id}` (cualquier subconjunto de `nombre`/`direccion`/`contacto`/`activo`) — `activo: false` es el soft delete, no borra el registro (necesario porque `detalle_entrada`/`detalle_salida` ya pueden tener FKs apuntando a él).
- Igual para `/clientes`.

**Movimientos** (solo cabecera, sin auth por ahora):
- `POST /movimientos` — `{"tipo": "ENTRADA"|"SALIDA", "descripcion"?}`.
- `GET /movimientos`, `GET /movimientos?tipo=ENTRADA`, `GET /movimientos/{id}`.
- `PATCH /movimientos/{id}/cerrar` — cierra el movimiento (409 si ya estaba cerrado). Un movimiento cerrado ya no acepta nuevos detalles (409, aplicado también en la BD vía trigger).

**Detalle de entrada** (router y recurso propios, `/detalle-entrada`, sin auth por ahora):
- `POST /detalle-entrada` — `{"movimiento_id", "proveedor_id", "material_id", "peso_bruto", "tara", "descripcion"?}`. 409 si el movimiento no es ENTRADA o ya está cerrado; 400 si `proveedor_id`/`material_id` no existen; **409 si el proveedor o el material están inactivos** (`activo = false`); 400 si `peso_bruto <= tara`. `peso_neto` y `precio_compra` (snapshot del precio de compra vigente) se calculan solos.
- `GET /detalle-entrada`, `GET /detalle-entrada?movimiento_id=...`, `GET /detalle-entrada/{id}`.

**Detalle de salida** (router y recurso propios, `/detalle-salida`, sin auth por ahora):
- `POST /detalle-salida` — `{"movimiento_id", "cliente_id", "precio_venta", "pacas": [id, id, ...], "descripcion"?}`. Esto vende esas pacas específicas: 409 si el movimiento no es SALIDA o ya está cerrado, 400 si `cliente_id` no existe, **409 si el cliente está inactivo**, 404 si alguna paca no existe, 409 si alguna ya estaba vendida. `cantidad_pacas` en la respuesta es derivado (cuenta pacas ligadas), no una columna.
- `GET /detalle-salida`, `GET /detalle-salida?movimiento_id=...`, `GET /detalle-salida/{id}`.

**Pacas** (sin auth por ahora):
- `GET /pacas`, `GET /pacas?en_inventario=true`, `GET /pacas/{id}`.
- `POST /pacas` — `{"codigo", "material_id"}`. Nace siempre `en_inventario: true`. 400 si `material_id` no existe, 409 si el código ya existe **o si el material está inactivo**.

**Regla de negocio (agregada 2026-07-25): ningún detalle/paca puede referenciar una entidad inactiva.** Validado en dos capas: la BD lo garantiza siempre (trigger `BEFORE INSERT`, ver `base-datos/{movimientos,pacas}/triggers.sql` — imposible saltárselo ni con un INSERT directo), y el backend valida antes para devolver un 409 con mensaje legible en vez de dejar burbujear la excepción cruda de Postgres.

**Inventario** (solo lectura, sin auth por ahora):
- `GET /inventario` — material suelto acumulado por `material_id` (`peso_total`).
- `GET /inventario/pacas` — pacas actualmente en bodega por `material_id` (`cantidad`).

**Historiales** (los tres solo lectura, sin auth por ahora, routers independientes):
- `GET /historial-precios`, `GET /historial-precios?material_id=...` — cada cambio de `precio_actual` (`precio_anterior`, `precio_nuevo`, `fecha_cambio`).
- `GET /historial-kg`, `GET /historial-kg?material_id=...` — cada cambio al inventario de material suelto (`peso_anterior`, `peso_nuevo`, `fecha_cambio`), generado por cada `detalle_entrada`.
- `GET /historial-pacas`, `GET /historial-pacas?paca_id=...`, `GET /historial-pacas?material_id=...` — eventos de cada paca: `evento` (`ALTA` o `VENTA`), `detalle_salida_id` (solo en `VENTA`), `fecha`.

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

curl -X PATCH http://localhost:8000/materiales/1 \
  -H "Content-Type: application/json" -d '{"precio_actual": 2.00}'
# -> 200, sin necesitar token (ver nota de auth arriba)

curl http://localhost:8000/historial-precios?material_id=1
```

Los tres historiales se llenan solos (vía triggers de Postgres, `base-datos/{materiales,inventario,pacas}/triggers.sql`), nunca por lógica del backend.

## Tests

```bash
./venv/bin/pip install -r requirements-dev.txt   # pytest, pytest-asyncio, httpx (no van en requirements.txt de producción)
./venv/bin/pytest -v
```

Corren contra **tu base de datos real** (`DATABASE_URL` del `.env`), no contra una base separada ni contra sqlite -- necesario porque las reglas de negocio viven en triggers/constraints de Postgres (columnas `GENERATED`, `CHECK`, `RAISE EXCEPTION`), que sqlite no puede reproducir. Aun así **no dejan ningún dato**: cada test corre dentro de una transacción que se revierte al terminar (`tests/conftest.py`, fixture `db_session` con `join_transaction_mode="create_savepoint"` -- el mismo patrón documentado en los docs de SQLAlchemy para probar apps con sesión-por-request). El endpoint completo se prueba de verdad vía HTTP (`httpx.AsyncClient` + `ASGITransport`, sin levantar un servidor real), inyectando esa sesión con `app.dependency_overrides`.

Cobertura actual: `materiales` (código, precio, historial, activo), `auth` (login), `proveedores`/`clientes` (CRUD, activo), y el flujo completo de `movimientos`/`detalle_entrada`/`detalle_salida`/`pacas`/`inventario`/historiales (incluye las reglas de negocio: tipo de movimiento correcto, movimiento cerrado, pacas ya vendidas, FKs inválidas).
