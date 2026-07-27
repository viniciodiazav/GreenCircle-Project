"""Casos de lectura (404, listados sin filtro) que el resto de la suite no
cubre porque está enfocada en flujos de negocio, no en cada GET individual."""


async def _crear_material(client, nombre, precio=1.5):
    resp = await client.post("/materiales", json={"nombre": nombre, "precio_actual": precio})
    return resp.json()["id"]


async def _crear_movimiento(client, tipo):
    resp = await client.post("/movimientos", json={"tipo": tipo})
    return resp.json()["id"]


async def test_get_movimiento_no_encontrado_404(client):
    resp = await client.get("/movimientos/999999")
    assert resp.status_code == 404


async def test_get_paca_no_encontrada_404(client):
    resp = await client.get("/pacas/999999")
    assert resp.status_code == 404


async def test_get_detalle_entrada_no_encontrado_404(client):
    resp = await client.get("/detalle-entrada/999999")
    assert resp.status_code == 404


async def test_get_detalle_salida_no_encontrado_404(client):
    resp = await client.get("/detalle-salida/999999")
    assert resp.status_code == 404


async def test_get_pacas_filtra_por_en_inventario(client):
    material_id = await _crear_material(client, "Material Filtro Pacas")
    resp = await client.get("/pacas", params={"en_inventario": True})
    assert resp.status_code == 200
    assert all(item["en_inventario"] is True for item in resp.json()["items"])


async def test_get_historial_kg_sin_filtro_devuelve_lista(client):
    resp = await client.get("/historial-kg")
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_get_historial_precios_sin_filtro_devuelve_lista(client):
    resp = await client.get("/historial-precios")
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_get_historial_pacas_sin_filtro_devuelve_lista(client):
    resp = await client.get("/historial-pacas")
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_get_tickets_venta_sin_filtro_devuelve_lista(client):
    resp = await client.get("/tickets-venta")
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_get_tickets_compra_sin_filtro_devuelve_lista(client):
    resp = await client.get("/tickets-compra")
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_get_inventario_pacas_sin_filtro_devuelve_lista(client):
    resp = await client.get("/inventario/pacas")
    assert resp.status_code == 200
    assert "items" in resp.json()


async def test_movimiento_no_encontrado_al_patchear_404(client):
    resp = await client.patch("/movimientos/999999", json={"descripcion": "x"})
    assert resp.status_code == 404


async def test_movimiento_no_encontrado_al_cerrar_404(client):
    resp = await client.patch("/movimientos/999999/cerrar")
    assert resp.status_code == 404
