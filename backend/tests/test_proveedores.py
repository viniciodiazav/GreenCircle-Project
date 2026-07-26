async def test_crear_proveedor_activo_por_defecto(client):
    resp = await client.post("/proveedores", json={"nombre": "Proveedor Prueba Uno"})
    assert resp.status_code == 201
    assert resp.json()["activo"] is True


async def test_filtrar_activos_e_inactivos(client):
    activo = await client.post("/proveedores", json={"nombre": "Proveedor Activo Prueba"})
    assert activo.status_code == 201
    inactivo = await client.post("/proveedores", json={"nombre": "Proveedor Inactivo Prueba"})
    inactivo_id = inactivo.json()["id"]
    patch = await client.patch(f"/proveedores/{inactivo_id}", json={"activo": False})
    assert patch.status_code == 200
    assert patch.json()["activo"] is False

    solo_activos = await client.get("/proveedores", params={"activo": "true"})
    nombres_activos = [p["nombre"] for p in solo_activos.json()["items"]]
    assert "Proveedor Activo Prueba" in nombres_activos
    assert "Proveedor Inactivo Prueba" not in nombres_activos

    solo_inactivos = await client.get("/proveedores", params={"activo": "false"})
    nombres_inactivos = [p["nombre"] for p in solo_inactivos.json()["items"]]
    assert "Proveedor Inactivo Prueba" in nombres_inactivos
    assert "Proveedor Activo Prueba" not in nombres_inactivos

    sin_filtro = await client.get("/proveedores", params={"limit": 200})
    nombres = [p["nombre"] for p in sin_filtro.json()["items"]]
    assert "Proveedor Activo Prueba" in nombres
    assert "Proveedor Inactivo Prueba" in nombres


async def test_get_proveedor_no_encontrado_404(client):
    resp = await client.get("/proveedores/999999")
    assert resp.status_code == 404


async def test_patch_proveedor_actualiza_campos(client):
    creado = await client.post("/proveedores", json={"nombre": "Proveedor Editable"})
    proveedor_id = creado.json()["id"]

    resp = await client.patch(
        f"/proveedores/{proveedor_id}", json={"contacto": "555-0000", "direccion": "Calle Falsa 123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["contacto"] == "555-0000"
    assert data["direccion"] == "Calle Falsa 123"
    assert data["nombre"] == "Proveedor Editable"
