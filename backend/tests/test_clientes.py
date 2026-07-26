async def test_crear_cliente_activo_por_defecto(client):
    resp = await client.post("/clientes", json={"nombre": "Cliente Prueba Uno"})
    assert resp.status_code == 201
    assert resp.json()["activo"] is True


async def test_filtrar_activos_e_inactivos(client):
    activo = await client.post("/clientes", json={"nombre": "Cliente Activo Prueba"})
    assert activo.status_code == 201
    inactivo = await client.post("/clientes", json={"nombre": "Cliente Inactivo Prueba"})
    inactivo_id = inactivo.json()["id"]
    patch = await client.patch(f"/clientes/{inactivo_id}", json={"activo": False})
    assert patch.status_code == 200
    assert patch.json()["activo"] is False

    solo_activos = await client.get("/clientes", params={"activo": "true"})
    nombres_activos = [c["nombre"] for c in solo_activos.json()["items"]]
    assert "Cliente Activo Prueba" in nombres_activos
    assert "Cliente Inactivo Prueba" not in nombres_activos

    solo_inactivos = await client.get("/clientes", params={"activo": "false"})
    nombres_inactivos = [c["nombre"] for c in solo_inactivos.json()["items"]]
    assert "Cliente Inactivo Prueba" in nombres_inactivos
    assert "Cliente Activo Prueba" not in nombres_inactivos


async def test_get_cliente_no_encontrado_404(client):
    resp = await client.get("/clientes/999999")
    assert resp.status_code == 404


async def test_patch_cliente_actualiza_campos(client):
    creado = await client.post("/clientes", json={"nombre": "Cliente Editable"})
    cliente_id = creado.json()["id"]

    resp = await client.patch(
        f"/clientes/{cliente_id}", json={"contacto": "555-1111", "direccion": "Avenida Siempreviva 742"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["contacto"] == "555-1111"
    assert data["direccion"] == "Avenida Siempreviva 742"
