async def test_crear_material_genera_codigo(client):
    resp = await client.post(
        "/materiales", json={"nombre": "Zincotest", "unidad": "kg", "precio_actual": 5.0}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["codigo"] == "ZINC"
    assert data["activo"] is True


async def test_crear_material_nombre_duplicado_409(client):
    payload = {"nombre": "Cobreprueba", "unidad": "kg", "precio_actual": 10.0}
    r1 = await client.post("/materiales", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/materiales", json=payload)
    assert r2.status_code == 409


async def test_crear_material_precio_invalido_422(client):
    resp = await client.post("/materiales", json={"nombre": "Materialmalo", "precio_actual": -1})
    assert resp.status_code == 422


async def test_patch_material_actualiza_precio_y_genera_historial(client):
    creado = await client.post("/materiales", json={"nombre": "Broncetest", "precio_actual": 3.0})
    material_id = creado.json()["id"]

    patch = await client.patch(f"/materiales/{material_id}", json={"precio_actual": 4.5})
    assert patch.status_code == 200
    assert patch.json()["precio_actual"] == 4.5

    historial = await client.get("/historial-precios", params={"material_id": material_id})
    assert historial.status_code == 200
    filas = historial.json()["items"]
    assert len(filas) == 1
    assert filas[0]["precio_anterior"] == 3.0
    assert filas[0]["precio_nuevo"] == 4.5


async def test_patch_material_sin_campos_400(client):
    creado = await client.post("/materiales", json={"nombre": "Latontest", "precio_actual": 2.0})
    material_id = creado.json()["id"]
    resp = await client.patch(f"/materiales/{material_id}", json={})
    assert resp.status_code == 400


async def test_patch_material_inexistente_404(client):
    resp = await client.patch("/materiales/999999", json={"precio_actual": 1.0})
    assert resp.status_code == 404


async def test_get_materiales_publico_solo_activos(client):
    creado = await client.post("/materiales", json={"nombre": "Estanotest", "precio_actual": 2.0})
    material_id = creado.json()["id"]
    await client.patch(f"/materiales/{material_id}", json={"activo": False})

    publico = await client.get("/materiales")
    nombres = [m["nombre"] for m in publico.json()["items"]]
    assert "Estanotest" not in nombres

    admin = await client.get("/materiales/admin")
    nombres_admin = [m["nombre"] for m in admin.json()["items"]]
    assert "Estanotest" in nombres_admin
