async def test_forma_de_respuesta_paginada(client):
    await client.post("/proveedores", json={"nombre": "Paginacion Forma A"})
    resp = await client.get("/proveedores")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"items", "total", "limit", "offset"}
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert isinstance(data["items"], list)


async def test_paginacion_limit_offset(client):
    # No asume una BD vacía (puede haber proveedores de antes) -- pide todo
    # con un limit grande primero para tener el universo real contra el cual
    # comparar las páginas, en vez de hardcodear un total absoluto.
    baseline_total = (await client.get("/proveedores", params={"limit": 1})).json()["total"]

    for i in range(5):
        await client.post("/proveedores", json={"nombre": f"Paginacion Prov {i}"})

    completa = await client.get("/proveedores", params={"limit": 200})
    data_completa = completa.json()
    total = data_completa["total"]
    todos = data_completa["items"]
    assert total == baseline_total + 5
    assert len(todos) == total

    pagina_1 = await client.get("/proveedores", params={"limit": 2, "offset": 0})
    data_1 = pagina_1.json()
    assert data_1["items"] == todos[0:2]
    assert data_1["total"] == total
    assert data_1["limit"] == 2
    assert data_1["offset"] == 0

    pagina_2 = await client.get("/proveedores", params={"limit": 2, "offset": 2})
    data_2 = pagina_2.json()
    assert data_2["items"] == todos[2:4]
    assert data_2["total"] == total

    pagina_final = await client.get("/proveedores", params={"limit": 2, "offset": total - 1})
    assert len(pagina_final.json()["items"]) == 1
    assert pagina_final.json()["items"][0] == todos[-1]


async def test_paginacion_limit_invalido_422(client):
    resp = await client.get("/proveedores", params={"limit": 0})
    assert resp.status_code == 422

    resp = await client.get("/proveedores", params={"limit": 500})
    assert resp.status_code == 422


async def test_paginacion_offset_negativo_422(client):
    resp = await client.get("/proveedores", params={"offset": -1})
    assert resp.status_code == 422


async def test_paginacion_detalle_salida_con_join(client):
    """detalle_salida pagina con un JOIN + count(pacas) -- caso especial que
    no usa el helper genérico ejecutar_paginado, se prueba aparte."""
    material = await client.post("/materiales", json={"nombre": "Paginacion Material", "precio_actual": 1})
    material_id = material.json()["id"]
    proveedor_id = (await client.post("/proveedores", json={"nombre": "Paginacion Prov Salida"})).json()["id"]
    cliente_id = (await client.post("/clientes", json={"nombre": "Paginacion Cliente"})).json()["id"]

    mov_entrada = (await client.post("/movimientos", json={"tipo": "ENTRADA"})).json()["id"]
    await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": mov_entrada,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 100,
            "tara": 1,
            "monto_total": 100,
        },
    )

    mov_salida = (await client.post("/movimientos", json={"tipo": "SALIDA"})).json()["id"]
    for _ in range(3):
        paca_id = (await client.post("/pacas", json={"material_id": material_id, "peso": 5})).json()["id"]
        await client.post(
            "/detalle-salida",
            json={
                "movimiento_id": mov_salida,
                "cliente_id": cliente_id,
                "precio_venta": 5.0,
                "monto_total": 25.0,
                "pacas": [paca_id],
            },
        )

    resp = await client.get("/detalle-salida", params={"movimiento_id": mov_salida, "limit": 2})
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    for item in data["items"]:
        assert item["cantidad_pacas"] == 1
