"""Permisos por rol -- ver base-datos/README.md para la tabla completa.
Operador: ver todo + crear/editar/cerrar/cancelar movimientos, detalles y
pacas. Solo Administrador: precios de materiales, alta/baja de
materiales/proveedores/clientes, ajustes de inventario, gestión de usuarios.
"""


async def _crear_material(client, nombre, precio=1.5):
    resp = await client.post("/materiales", json={"nombre": nombre, "precio_actual": precio})
    return resp.json()["id"]


async def _crear_proveedor(client, nombre):
    resp = await client.post("/proveedores", json={"nombre": nombre})
    return resp.json()["id"]


async def _crear_movimiento(client, tipo):
    resp = await client.post("/movimientos", json={"tipo": tipo})
    return resp.json()["id"]


# -- Operador: rechazado en lo admin-only --


async def test_operador_no_puede_crear_material_403(client_operador):
    resp = await client_operador.post("/materiales", json={"nombre": "X", "precio_actual": 1})
    assert resp.status_code == 403


async def test_operador_no_puede_editar_material_403(client, client_operador):
    material_id = await _crear_material(client, "Material Rol Test")
    resp = await client_operador.patch(f"/materiales/{material_id}", json={"precio_actual": 2})
    assert resp.status_code == 403


async def test_operador_no_puede_crear_proveedor_403(client_operador):
    resp = await client_operador.post("/proveedores", json={"nombre": "X"})
    assert resp.status_code == 403


async def test_operador_no_puede_crear_cliente_403(client_operador):
    resp = await client_operador.post("/clientes", json={"nombre": "X"})
    assert resp.status_code == 403


async def test_operador_no_puede_crear_ajuste_inventario_403(client, client_operador):
    material_id = await _crear_material(client, "Material Ajuste Rol Test")
    resp = await client_operador.post(
        "/ajustes-inventario",
        json={"material_id": material_id, "peso_ajuste": 5, "motivo": "conteo"},
    )
    assert resp.status_code == 403


async def test_operador_no_puede_listar_usuarios_403(client_operador):
    resp = await client_operador.get("/usuarios")
    assert resp.status_code == 403


async def test_operador_no_puede_crear_usuario_403(client_operador):
    resp = await client_operador.post(
        "/usuarios", json={"usuario": "x", "password": "clave12345"}
    )
    assert resp.status_code == 403


# -- Operador: sí puede el flujo diario --


async def test_operador_puede_ver_materiales_admin(client_operador):
    resp = await client_operador.get("/materiales/admin")
    assert resp.status_code == 200


async def test_operador_puede_crear_y_cancelar_movimiento(client, client_operador):
    # material/proveedor los crea el admin (client), el flujo de movimiento
    # lo hace el operador.
    proveedor_id = await _crear_proveedor(client, "Proveedor Rol Test")
    material_id = await _crear_material(client, "Material Movimiento Rol Test")

    movimiento_id = await _crear_movimiento(client_operador, "ENTRADA")
    detalle = await client_operador.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 20,
            "tara": 2,
            "monto_total": 50,
        },
    )
    assert detalle.status_code == 201
    detalle_id = detalle.json()["id"]

    cancelar = await client_operador.delete(f"/detalle-entrada/{detalle_id}")
    assert cancelar.status_code == 204

    cancelar_movimiento = await client_operador.delete(f"/movimientos/{movimiento_id}")
    assert cancelar_movimiento.status_code == 204


async def test_usuario_creado_tiene_rol_default_operador(client):
    resp = await client.post(
        "/usuarios", json={"usuario": "usuario_rol_default", "password": "clave12345"}
    )
    assert resp.status_code == 201
    assert resp.json()["rol"] == "operador"


async def test_admin_puede_cambiar_rol_de_usuario(client, usuario_operador_test):
    resp = await client.patch(
        f"/usuarios/{usuario_operador_test.id}", json={"rol": "administrador"}
    )
    assert resp.status_code == 200
    assert resp.json()["rol"] == "administrador"
