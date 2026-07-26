async def _crear_proveedor(client, nombre):
    resp = await client.post("/proveedores", json={"nombre": nombre})
    return resp.json()["id"]


async def _crear_cliente(client, nombre):
    resp = await client.post("/clientes", json={"nombre": nombre})
    return resp.json()["id"]


async def _crear_material(client, nombre, precio=1.5):
    resp = await client.post("/materiales", json={"nombre": nombre, "precio_actual": precio})
    return resp.json()["id"]


async def _crear_movimiento(client, tipo):
    resp = await client.post("/movimientos", json={"tipo": tipo})
    return resp.json()["id"]


async def _agregar_detalle_entrada(client, movimiento_id, proveedor_id, material_id, peso_bruto=50, tara=5):
    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": peso_bruto,
            "tara": tara,
            "monto_total": 100,
        },
    )
    return resp.json()


async def _peso_total(client, material_id):
    inventario = await client.get("/inventario")
    fila = next(f for f in inventario.json()["items"] if f["material_id"] == material_id)
    return fila["peso_total"]


# ---------- editar/cancelar movimiento ----------


async def test_editar_descripcion_movimiento(client):
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    resp = await client.patch(f"/movimientos/{movimiento_id}", json={"descripcion": "Nueva descripcion"})
    assert resp.status_code == 200
    assert resp.json()["descripcion"] == "Nueva descripcion"


async def test_editar_descripcion_movimiento_cerrado_permitido(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Editar Cerrado")
    material_id = await _crear_material(client, "Material Editar Cerrado")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    await _agregar_detalle_entrada(client, movimiento_id, proveedor_id, material_id)
    await client.patch(f"/movimientos/{movimiento_id}/cerrar")

    resp = await client.patch(f"/movimientos/{movimiento_id}", json={"descripcion": "Corregido despues"})
    assert resp.status_code == 200
    assert resp.json()["descripcion"] == "Corregido despues"


async def test_cancelar_movimiento_vacio(client):
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    resp = await client.delete(f"/movimientos/{movimiento_id}")
    assert resp.status_code == 204

    verificar = await client.get(f"/movimientos/{movimiento_id}")
    assert verificar.status_code == 404


async def test_cancelar_movimiento_con_detalles_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Cancelar Con Detalles")
    material_id = await _crear_material(client, "Material Cancelar Con Detalles")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    await _agregar_detalle_entrada(client, movimiento_id, proveedor_id, material_id)

    resp = await client.delete(f"/movimientos/{movimiento_id}")
    assert resp.status_code == 409


async def test_cancelar_movimiento_cerrado_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Cancelar Cerrado")
    material_id = await _crear_material(client, "Material Cancelar Cerrado")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    await _agregar_detalle_entrada(client, movimiento_id, proveedor_id, material_id)
    await client.patch(f"/movimientos/{movimiento_id}/cerrar")

    resp = await client.delete(f"/movimientos/{movimiento_id}")
    assert resp.status_code == 409


# ---------- editar/cancelar detalle_entrada ----------


async def test_editar_detalle_entrada_ajusta_inventario_por_delta(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Editar Entrada")
    material_id = await _crear_material(client, "Material Editar Entrada")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    detalle = await _agregar_detalle_entrada(
        client, movimiento_id, proveedor_id, material_id, peso_bruto=50, tara=5
    )
    assert detalle["peso_neto"] == 45.0
    assert await _peso_total(client, material_id) == 45.0

    resp = await client.patch(f"/detalle-entrada/{detalle['id']}", json={"peso_bruto": 70})
    assert resp.status_code == 200
    assert resp.json()["peso_neto"] == 65.0
    # delta = 65 - 45 = +20 sobre el inventario ya sincronizado
    assert await _peso_total(client, material_id) == 65.0


async def test_editar_detalle_entrada_actualiza_monto_total_y_descripcion(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Editar Monto")
    material_id = await _crear_material(client, "Material Editar Monto")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    detalle = await _agregar_detalle_entrada(client, movimiento_id, proveedor_id, material_id)

    resp = await client.patch(
        f"/detalle-entrada/{detalle['id']}",
        json={"monto_total": 250.5, "descripcion": "Corregido"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["monto_total"] == 250.5
    assert data["descripcion"] == "Corregido"


async def test_editar_detalle_entrada_peso_bruto_menor_que_tara_400(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Editar Invalido")
    material_id = await _crear_material(client, "Material Editar Invalido")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    detalle = await _agregar_detalle_entrada(client, movimiento_id, proveedor_id, material_id)

    resp = await client.patch(f"/detalle-entrada/{detalle['id']}", json={"peso_bruto": 2, "tara": 5})
    assert resp.status_code == 400


async def test_editar_detalle_entrada_movimiento_cerrado_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Editar Cerrado Detalle")
    material_id = await _crear_material(client, "Material Editar Cerrado Detalle")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    detalle = await _agregar_detalle_entrada(client, movimiento_id, proveedor_id, material_id)
    await client.patch(f"/movimientos/{movimiento_id}/cerrar")

    resp = await client.patch(f"/detalle-entrada/{detalle['id']}", json={"monto_total": 999})
    assert resp.status_code == 409


async def test_cancelar_detalle_entrada_revierte_inventario(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Cancelar Entrada")
    material_id = await _crear_material(client, "Material Cancelar Entrada")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    detalle = await _agregar_detalle_entrada(
        client, movimiento_id, proveedor_id, material_id, peso_bruto=50, tara=5
    )
    assert await _peso_total(client, material_id) == 45.0

    resp = await client.delete(f"/detalle-entrada/{detalle['id']}")
    assert resp.status_code == 204

    assert await _peso_total(client, material_id) == 0.0

    verificar = await client.get(f"/detalle-entrada/{detalle['id']}")
    assert verificar.status_code == 404


async def test_cancelar_detalle_entrada_movimiento_cerrado_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Cancelar Cerrado Detalle")
    material_id = await _crear_material(client, "Material Cancelar Cerrado Detalle")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    detalle = await _agregar_detalle_entrada(client, movimiento_id, proveedor_id, material_id)
    await client.patch(f"/movimientos/{movimiento_id}/cerrar")

    resp = await client.delete(f"/detalle-entrada/{detalle['id']}")
    assert resp.status_code == 409


async def test_cancelar_detalle_entrada_inventario_ya_usado_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Cancelar Usado")
    material_id = await _crear_material(client, "Material Cancelar Usado")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    detalle = await _agregar_detalle_entrada(
        client, movimiento_id, proveedor_id, material_id, peso_bruto=50, tara=5
    )
    # peso_neto = 45; se compacta una paca de 40, dejando solo 5 disponibles
    paca = await client.post("/pacas", json={"material_id": material_id, "peso": 40})
    assert paca.status_code == 201

    resp = await client.delete(f"/detalle-entrada/{detalle['id']}")
    assert resp.status_code == 409
    # el detalle sigue existiendo -- la cancelacion no se aplico
    verificar = await client.get(f"/detalle-entrada/{detalle['id']}")
    assert verificar.status_code == 200


# ---------- editar/cancelar detalle_salida ----------


async def test_editar_detalle_salida_precio_y_monto(client):
    material_id = await _crear_material(client, "Material Editar Salida")
    cliente_id = await _crear_cliente(client, "Cliente Editar Salida")
    proveedor_id = await _crear_proveedor(client, "Proveedor Editar Salida")
    mov_entrada = await _crear_movimiento(client, "ENTRADA")
    await _agregar_detalle_entrada(client, mov_entrada, proveedor_id, material_id, peso_bruto=30, tara=1)
    paca = await client.post("/pacas", json={"material_id": material_id, "peso": 10})
    paca_id = paca.json()["id"]

    movimiento_id = await _crear_movimiento(client, "SALIDA")
    detalle = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": 50.0,
            "pacas": [paca_id],
        },
    )
    detalle_id = detalle.json()["id"]

    resp = await client.patch(
        f"/detalle-salida/{detalle_id}", json={"precio_venta": 6.5, "monto_total": 65.0}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["precio_venta"] == 6.5
    assert data["monto_total"] == 65.0
    assert data["cantidad_pacas"] == 1


async def test_editar_detalle_salida_movimiento_cerrado_409(client):
    material_id = await _crear_material(client, "Material Editar Salida Cerrado")
    cliente_id = await _crear_cliente(client, "Cliente Editar Salida Cerrado")
    proveedor_id = await _crear_proveedor(client, "Proveedor Editar Salida Cerrado")
    mov_entrada = await _crear_movimiento(client, "ENTRADA")
    await _agregar_detalle_entrada(client, mov_entrada, proveedor_id, material_id, peso_bruto=30, tara=1)
    paca_id = (await client.post("/pacas", json={"material_id": material_id, "peso": 10})).json()["id"]

    movimiento_id = await _crear_movimiento(client, "SALIDA")
    detalle = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": 50.0,
            "pacas": [paca_id],
        },
    )
    detalle_id = detalle.json()["id"]
    await client.patch(f"/movimientos/{movimiento_id}/cerrar")

    resp = await client.patch(f"/detalle-salida/{detalle_id}", json={"monto_total": 999})
    assert resp.status_code == 409


async def test_cancelar_detalle_salida_libera_pacas(client):
    material_id = await _crear_material(client, "Material Cancelar Salida")
    cliente_id = await _crear_cliente(client, "Cliente Cancelar Salida")
    proveedor_id = await _crear_proveedor(client, "Proveedor Cancelar Salida")
    mov_entrada = await _crear_movimiento(client, "ENTRADA")
    await _agregar_detalle_entrada(client, mov_entrada, proveedor_id, material_id, peso_bruto=30, tara=1)
    paca = await client.post("/pacas", json={"material_id": material_id, "peso": 10})
    paca_id = paca.json()["id"]

    movimiento_id = await _crear_movimiento(client, "SALIDA")
    detalle = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": 50.0,
            "pacas": [paca_id],
        },
    )
    detalle_id = detalle.json()["id"]

    inventario_pacas_antes = await client.get("/inventario/pacas")
    fila_antes = next(
        f for f in inventario_pacas_antes.json()["items"] if f["material_id"] == material_id
    )
    assert fila_antes["cantidad"] == 0

    resp = await client.delete(f"/detalle-salida/{detalle_id}")
    assert resp.status_code == 204

    paca_actualizada = (await client.get(f"/pacas/{paca_id}")).json()
    assert paca_actualizada["en_inventario"] is True
    assert paca_actualizada["detalle_salida_id"] is None

    inventario_pacas_despues = await client.get("/inventario/pacas")
    fila_despues = next(
        f for f in inventario_pacas_despues.json()["items"] if f["material_id"] == material_id
    )
    assert fila_despues["cantidad"] == 1

    historial = await client.get("/historial-pacas", params={"paca_id": paca_id})
    eventos = [f["evento"] for f in historial.json()["items"]]
    assert eventos.count("ALTA") == 1
    assert eventos.count("VENTA") == 1
    assert eventos.count("CANCELACION") == 1

    verificar = await client.get(f"/detalle-salida/{detalle_id}")
    assert verificar.status_code == 404


async def test_cancelar_detalle_salida_movimiento_cerrado_409(client):
    material_id = await _crear_material(client, "Material Cancelar Salida Cerrado")
    cliente_id = await _crear_cliente(client, "Cliente Cancelar Salida Cerrado")
    proveedor_id = await _crear_proveedor(client, "Proveedor Cancelar Salida Cerrado")
    mov_entrada = await _crear_movimiento(client, "ENTRADA")
    await _agregar_detalle_entrada(client, mov_entrada, proveedor_id, material_id, peso_bruto=30, tara=1)
    paca_id = (await client.post("/pacas", json={"material_id": material_id, "peso": 10})).json()["id"]

    movimiento_id = await _crear_movimiento(client, "SALIDA")
    detalle = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": 50.0,
            "pacas": [paca_id],
        },
    )
    detalle_id = detalle.json()["id"]
    await client.patch(f"/movimientos/{movimiento_id}/cerrar")

    resp = await client.delete(f"/detalle-salida/{detalle_id}")
    assert resp.status_code == 409
