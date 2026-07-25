async def _crear_material(client, nombre, precio=1.5):
    resp = await client.post("/materiales", json={"nombre": nombre, "precio_actual": precio})
    return resp.json()["id"]


async def _crear_proveedor(client, nombre):
    resp = await client.post("/proveedores", json={"nombre": nombre})
    return resp.json()["id"]


async def _agregar_inventario(client, material_id, peso):
    proveedor_id = await _crear_proveedor(client, "Proveedor Ajuste Inventario")
    movimiento = await client.post("/movimientos", json={"tipo": "ENTRADA"})
    movimiento_id = movimiento.json()["id"]
    await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": peso + 1,
            "tara": 1,
        },
    )


async def test_ajuste_negativo_resta_inventario(client):
    material_id = await _crear_material(client, "Material Ajuste Negativo")
    await _agregar_inventario(client, material_id, peso=50)

    resp = await client.post(
        "/ajustes-inventario",
        json={"material_id": material_id, "peso_ajuste": -5.5, "motivo": "Merma por humedad"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["peso_ajuste"] == -5.5
    assert data["motivo"] == "Merma por humedad"
    assert data["comentarios"] is None

    inventario = await client.get("/inventario")
    fila = next(f for f in inventario.json() if f["material_id"] == material_id)
    assert fila["peso_total"] == 44.5

    historial = await client.get("/historial-kg", params={"material_id": material_id})
    filas = sorted(historial.json(), key=lambda f: f["fecha_cambio"])
    assert filas[-1]["peso_anterior"] == 50.0
    assert filas[-1]["peso_nuevo"] == 44.5


async def test_ajuste_positivo_suma_inventario(client):
    material_id = await _crear_material(client, "Material Ajuste Positivo")
    await _agregar_inventario(client, material_id, peso=20)

    resp = await client.post(
        "/ajustes-inventario",
        json={
            "material_id": material_id,
            "peso_ajuste": 3.2,
            "motivo": "Conteo físico encontró más material",
            "comentarios": "Se recontó dos veces para confirmar",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["comentarios"] == "Se recontó dos veces para confirmar"

    inventario = await client.get("/inventario")
    fila = next(f for f in inventario.json() if f["material_id"] == material_id)
    assert fila["peso_total"] == 23.2


async def test_ajuste_motivo_vacio_422(client):
    material_id = await _crear_material(client, "Material Ajuste Sin Motivo")
    await _agregar_inventario(client, material_id, peso=10)

    resp = await client.post(
        "/ajustes-inventario",
        json={"material_id": material_id, "peso_ajuste": -1, "motivo": ""},
    )
    assert resp.status_code == 422


async def test_ajuste_motivo_faltante_422(client):
    material_id = await _crear_material(client, "Material Ajuste Motivo Faltante")
    await _agregar_inventario(client, material_id, peso=10)

    resp = await client.post(
        "/ajustes-inventario", json={"material_id": material_id, "peso_ajuste": -1}
    )
    assert resp.status_code == 422


async def test_ajuste_cero_422(client):
    material_id = await _crear_material(client, "Material Ajuste Cero")
    await _agregar_inventario(client, material_id, peso=10)

    resp = await client.post(
        "/ajustes-inventario",
        json={"material_id": material_id, "peso_ajuste": 0, "motivo": "Sin cambio"},
    )
    assert resp.status_code == 422


async def test_ajuste_deja_inventario_negativo_409(client):
    material_id = await _crear_material(client, "Material Ajuste Excesivo")
    await _agregar_inventario(client, material_id, peso=10)

    resp = await client.post(
        "/ajustes-inventario",
        json={"material_id": material_id, "peso_ajuste": -50, "motivo": "Merma enorme"},
    )
    assert resp.status_code == 409


async def test_ajuste_material_invalido_400(client):
    resp = await client.post(
        "/ajustes-inventario",
        json={"material_id": 999999, "peso_ajuste": -1, "motivo": "Material inexistente"},
    )
    assert resp.status_code == 400


async def test_listar_ajustes_filtra_por_material(client):
    material_id = await _crear_material(client, "Material Ajuste Filtro")
    await _agregar_inventario(client, material_id, peso=10)
    await client.post(
        "/ajustes-inventario",
        json={"material_id": material_id, "peso_ajuste": -2, "motivo": "Merma"},
    )

    resp = await client.get("/ajustes-inventario", params={"material_id": material_id})
    assert resp.status_code == 200
    filas = resp.json()
    assert len(filas) == 1
    assert filas[0]["material_id"] == material_id
