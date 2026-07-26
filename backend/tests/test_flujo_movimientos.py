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


async def _agregar_inventario(client, material_id, peso):
    """Registra una entrada con peso_neto == peso, para que haya inventario
    suelto suficiente antes de compactar una paca de ese material."""
    proveedor_id = await _crear_proveedor(client, "Proveedor Auto Inventario")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": peso + 1,
            "tara": 1,
            "monto_total": 100,
        },
    )


async def _crear_paca(client, material_id, peso=10):
    await _agregar_inventario(client, material_id, peso)
    resp = await client.post("/pacas", json={"material_id": material_id, "peso": peso})
    return resp.json()


async def test_movimiento_tipo_invalido_422(client):
    resp = await client.post("/movimientos", json={"tipo": "OTRO"})
    assert resp.status_code == 422


async def test_detalle_entrada_calcula_peso_neto_y_precio_compra(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Entrada A")
    material_id = await _crear_material(client, "Material Entrada A", precio=2.0)
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 100,
            "tara": 10,
            "monto_total": 100,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["peso_neto"] == 90.0
    assert data["precio_compra"] == 2.0
    assert data["descuento"] == 0


async def test_detalle_entrada_descuento_afecta_peso_neto(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Entrada Descuento")
    material_id = await _crear_material(client, "Material Entrada Descuento")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 100,
            "tara": 10,
            "monto_total": 100,
            "descuento": 20,
            "descripcion_descuento": "Material húmedo",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    # peso_neto = (100 - 10) * (1 - 20/100) = 90 * 0.8 = 72
    assert data["peso_neto"] == 72.0
    assert data["descuento"] == 20
    assert data["descripcion_descuento"] == "Material húmedo"


async def test_detalle_entrada_descuento_fuera_de_rango_422(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Entrada Descuento Malo")
    material_id = await _crear_material(client, "Material Entrada Descuento Malo")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 100,
            "tara": 10,
            "monto_total": 100,
            "descuento": 150,
        },
    )
    assert resp.status_code == 422


async def test_detalle_entrada_movimiento_tipo_incorrecto_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Entrada B")
    material_id = await _crear_material(client, "Material Entrada B")
    movimiento_id = await _crear_movimiento(client, "SALIDA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": 100,
        },
    )
    assert resp.status_code == 409


async def test_detalle_entrada_movimiento_cerrado_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Entrada C")
    material_id = await _crear_material(client, "Material Entrada C")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    primera = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": 100,
        },
    )
    assert primera.status_code == 201

    cerrar = await client.patch(f"/movimientos/{movimiento_id}/cerrar")
    assert cerrar.status_code == 200

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": 100,
        },
    )
    assert resp.status_code == 409


async def test_detalle_entrada_fk_invalida_400(client):
    material_id = await _crear_material(client, "Material Entrada D")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": 999999,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": 100,
        },
    )
    assert resp.status_code == 400


async def test_entrada_sincroniza_inventario_e_historial_kg(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Entrada E")
    material_id = await _crear_material(client, "Material Entrada E")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 80,
            "tara": 10,
            "monto_total": 100,
        },
    )
    assert resp.status_code == 201

    inventario = await client.get("/inventario")
    fila = next(f for f in inventario.json()["items"] if f["material_id"] == material_id)
    assert fila["peso_total"] == 70.0

    historial = await client.get("/historial-kg", params={"material_id": material_id})
    filas = historial.json()["items"]
    assert len(filas) == 1
    assert filas[0]["peso_anterior"] == 0.0
    assert filas[0]["peso_nuevo"] == 70.0


async def test_registrar_paca_resta_inventario_y_registra_historial(client):
    material_id = await _crear_material(client, "Material Resta Inventario")
    await _agregar_inventario(client, material_id, peso=100)

    inventario_antes = await client.get("/inventario")
    fila_antes = next(f for f in inventario_antes.json()["items"] if f["material_id"] == material_id)
    assert fila_antes["peso_total"] == 100.0

    paca = await client.post("/pacas", json={"material_id": material_id, "peso": 30})
    assert paca.status_code == 201

    inventario_despues = await client.get("/inventario")
    fila_despues = next(f for f in inventario_despues.json()["items"] if f["material_id"] == material_id)
    assert fila_despues["peso_total"] == 70.0

    historial = await client.get("/historial-kg", params={"material_id": material_id})
    filas = sorted(historial.json()["items"], key=lambda f: f["fecha_cambio"])
    assert filas[-1]["peso_anterior"] == 100.0
    assert filas[-1]["peso_nuevo"] == 70.0


async def test_registrar_paca_inventario_insuficiente_409(client):
    material_id = await _crear_material(client, "Material Sin Inventario")

    resp = await client.post("/pacas", json={"material_id": material_id, "peso": 5})
    assert resp.status_code == 409


async def test_registrar_paca_genera_codigo_y_correlativo(client):
    material = await client.post(
        "/materiales", json={"nombre": "Materialcodigopaca", "precio_actual": 1.0}
    )
    material_data = material.json()
    material_id = material_data["id"]
    codigo_material = material_data["codigo"]

    r1 = await _crear_paca(client, material_id, peso=15.5)
    assert r1["en_inventario"] is True
    assert r1["detalle_salida_id"] is None
    assert r1["peso"] == 15.5

    fecha = r1["fecha_registro"][:10].replace("-", "")
    assert r1["codigo"] == f"{codigo_material}-{fecha}-01"

    r2 = await _crear_paca(client, material_id, peso=8)
    assert r2["codigo"] == f"{codigo_material}-{fecha}-02"


async def test_registrar_paca_peso_invalido_422(client):
    material_id = await _crear_material(client, "Material Paca Peso Malo")
    resp = await client.post("/pacas", json={"material_id": material_id, "peso": 0})
    assert resp.status_code == 422


async def test_historial_pacas_registra_alta(client):
    material_id = await _crear_material(client, "Material Paca B")
    paca_id = (await _crear_paca(client, material_id))["id"]

    historial = await client.get("/historial-pacas", params={"paca_id": paca_id})
    filas = historial.json()["items"]
    assert len(filas) == 1
    assert filas[0]["evento"] == "ALTA"
    assert filas[0]["detalle_salida_id"] is None


async def test_venta_completa_actualiza_todo(client):
    material_id = await _crear_material(client, "Material Venta A")
    cliente_id = await _crear_cliente(client, "Cliente Venta A")
    paca_id = (await _crear_paca(client, material_id))["id"]
    movimiento_id = await _crear_movimiento(client, "SALIDA")

    resp = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 9.5,
            "monto_total": 100,
            "pacas": [paca_id],
        },
    )
    assert resp.status_code == 201
    detalle = resp.json()
    assert detalle["cantidad_pacas"] == 1

    paca_actualizada = (await client.get(f"/pacas/{paca_id}")).json()
    assert paca_actualizada["en_inventario"] is False
    assert paca_actualizada["detalle_salida_id"] == detalle["id"]

    inventario_pacas = await client.get("/inventario/pacas")
    fila = next(f for f in inventario_pacas.json()["items"] if f["material_id"] == material_id)
    assert fila["cantidad"] == 0

    historial = await client.get("/historial-pacas", params={"paca_id": paca_id})
    eventos = {f["evento"] for f in historial.json()["items"]}
    assert eventos == {"ALTA", "VENTA"}

    detalle_salida_get = await client.get("/detalle-salida", params={"movimiento_id": movimiento_id})
    assert detalle_salida_get.json()["items"][0]["cantidad_pacas"] == 1


async def test_vender_paca_ya_vendida_409(client):
    material_id = await _crear_material(client, "Material Venta B")
    cliente_id = await _crear_cliente(client, "Cliente Venta B")
    paca_id = (await _crear_paca(client, material_id))["id"]
    movimiento_id = await _crear_movimiento(client, "SALIDA")

    primera = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": 100,
            "pacas": [paca_id],
        },
    )
    assert primera.status_code == 201

    otro_movimiento_id = await _crear_movimiento(client, "SALIDA")
    resp = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": otro_movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": 100,
            "pacas": [paca_id],
        },
    )
    assert resp.status_code == 409


async def test_vender_paca_inexistente_404(client):
    cliente_id = await _crear_cliente(client, "Cliente Venta C")
    movimiento_id = await _crear_movimiento(client, "SALIDA")
    resp = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": 100,
            "pacas": [999999],
        },
    )
    assert resp.status_code == 404


async def test_vender_en_movimiento_tipo_incorrecto_409(client):
    material_id = await _crear_material(client, "Material Venta D")
    cliente_id = await _crear_cliente(client, "Cliente Venta D")
    paca_id = (await _crear_paca(client, material_id))["id"]
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": 100,
            "pacas": [paca_id],
        },
    )
    assert resp.status_code == 409


async def test_vender_cliente_invalido_400(client):
    material_id = await _crear_material(client, "Material Venta E")
    paca_id = (await _crear_paca(client, material_id))["id"]
    movimiento_id = await _crear_movimiento(client, "SALIDA")

    resp = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": 999999,
            "precio_venta": 5.0,
            "monto_total": 100,
            "pacas": [paca_id],
        },
    )
    assert resp.status_code == 400


async def test_cerrar_movimiento_dos_veces_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Cerrar Dos Veces")
    material_id = await _crear_material(client, "Material Cerrar Dos Veces")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": 100,
        },
    )

    r1 = await client.patch(f"/movimientos/{movimiento_id}/cerrar")
    assert r1.status_code == 200
    assert r1.json()["cerrado"] is True
    r2 = await client.patch(f"/movimientos/{movimiento_id}/cerrar")
    assert r2.status_code == 409


async def test_listar_movimientos_filtra_por_tipo(client):
    entrada_id = await _crear_movimiento(client, "ENTRADA")
    salida_id = await _crear_movimiento(client, "SALIDA")

    entradas = await client.get("/movimientos", params={"tipo": "ENTRADA"})
    ids_entrada = [m["id"] for m in entradas.json()["items"]]
    assert entrada_id in ids_entrada
    assert salida_id not in ids_entrada


async def test_detalle_entrada_proveedor_inactivo_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Inactivo Flujo")
    await client.patch(f"/proveedores/{proveedor_id}", json={"activo": False})
    material_id = await _crear_material(client, "Material Flujo Prov Inactivo")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": 100,
        },
    )
    assert resp.status_code == 409


async def test_detalle_entrada_material_inactivo_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Flujo Mat Inactivo")
    material_id = await _crear_material(client, "Material Inactivo Flujo")
    await client.patch(f"/materiales/{material_id}", json={"activo": False})
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": 100,
        },
    )
    assert resp.status_code == 409


async def test_detalle_salida_cliente_inactivo_409(client):
    material_id = await _crear_material(client, "Material Flujo Cli Inactivo")
    cliente_id = await _crear_cliente(client, "Cliente Inactivo Flujo")
    await client.patch(f"/clientes/{cliente_id}", json={"activo": False})
    paca_id = (await _crear_paca(client, material_id))["id"]
    movimiento_id = await _crear_movimiento(client, "SALIDA")

    resp = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": 100,
            "pacas": [paca_id],
        },
    )
    assert resp.status_code == 409


async def test_registrar_paca_material_inactivo_409(client):
    material_id = await _crear_material(client, "Material Inactivo Paca")
    await client.patch(f"/materiales/{material_id}", json={"activo": False})

    resp = await client.post("/pacas", json={"material_id": material_id, "peso": 10})
    assert resp.status_code == 409


async def test_detalle_entrada_monto_total_faltante_422(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Monto Faltante")
    material_id = await _crear_material(client, "Material Monto Faltante")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
        },
    )
    assert resp.status_code == 422


async def test_detalle_entrada_monto_total_negativo_422(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Monto Negativo")
    material_id = await _crear_material(client, "Material Monto Negativo")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": -1,
        },
    )
    assert resp.status_code == 422


async def test_detalle_entrada_monto_total_cero_permitido(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Monto Cero")
    material_id = await _crear_material(client, "Material Monto Cero")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    resp = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": 0,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["monto_total"] == 0


async def test_detalle_salida_monto_total_negativo_422(client):
    material_id = await _crear_material(client, "Material Salida Monto Negativo")
    cliente_id = await _crear_cliente(client, "Cliente Salida Monto Negativo")
    paca_id = (await _crear_paca(client, material_id))["id"]
    movimiento_id = await _crear_movimiento(client, "SALIDA")

    resp = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": -10,
            "pacas": [paca_id],
        },
    )
    assert resp.status_code == 422


async def test_detalle_entrada_proveedor_distinto_mismo_movimiento_409(client):
    proveedor_a = await _crear_proveedor(client, "Proveedor Mezcla A")
    proveedor_b = await _crear_proveedor(client, "Proveedor Mezcla B")
    material_id = await _crear_material(client, "Material Mezcla Proveedor")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    primera = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_a,
            "material_id": material_id,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": 100,
        },
    )
    assert primera.status_code == 201

    segunda = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_b,
            "material_id": material_id,
            "peso_bruto": 30,
            "tara": 3,
            "monto_total": 60,
        },
    )
    assert segunda.status_code == 409

    # Un segundo detalle del mismo proveedor sí debe poder agregarse.
    tercera = await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_a,
            "material_id": material_id,
            "peso_bruto": 20,
            "tara": 2,
            "monto_total": 40,
        },
    )
    assert tercera.status_code == 201


async def test_detalle_salida_cliente_distinto_mismo_movimiento_409(client):
    material_id = await _crear_material(client, "Material Mezcla Cliente")
    cliente_a = await _crear_cliente(client, "Cliente Mezcla A")
    cliente_b = await _crear_cliente(client, "Cliente Mezcla B")
    paca_a = (await _crear_paca(client, material_id))["id"]
    paca_b = (await _crear_paca(client, material_id))["id"]
    movimiento_id = await _crear_movimiento(client, "SALIDA")

    primera = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_a,
            "precio_venta": 5.0,
            "monto_total": 50,
            "pacas": [paca_a],
        },
    )
    assert primera.status_code == 201

    segunda = await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_b,
            "precio_venta": 5.0,
            "monto_total": 50,
            "pacas": [paca_b],
        },
    )
    assert segunda.status_code == 409


async def test_cerrar_movimiento_entrada_sin_detalles_409(client):
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    resp = await client.patch(f"/movimientos/{movimiento_id}/cerrar")
    assert resp.status_code == 409


async def test_cerrar_movimiento_salida_sin_detalles_409(client):
    movimiento_id = await _crear_movimiento(client, "SALIDA")
    resp = await client.patch(f"/movimientos/{movimiento_id}/cerrar")
    assert resp.status_code == 409


async def test_ticket_compra_se_genera_al_cerrar_movimiento_entrada(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Ticket Compra")
    material_a = await _crear_material(client, "Material Ticket Compra A")
    material_b = await _crear_material(client, "Material Ticket Compra B")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")

    await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_a,
            "peso_bruto": 50,
            "tara": 5,
            "monto_total": 100,
        },
    )
    await client.post(
        "/detalle-entrada",
        json={
            "movimiento_id": movimiento_id,
            "proveedor_id": proveedor_id,
            "material_id": material_b,
            "peso_bruto": 30,
            "tara": 3,
            "monto_total": 60,
        },
    )

    # Antes de cerrar no debe existir ticket todavía.
    antes = await client.get("/tickets-compra", params={"movimiento_id": movimiento_id})
    assert antes.json()["items"] == []

    cerrar = await client.patch(f"/movimientos/{movimiento_id}/cerrar")
    assert cerrar.status_code == 200
    fecha_cierre = cerrar.json()["fecha"]

    despues = await client.get("/tickets-compra", params={"movimiento_id": movimiento_id})
    tickets = despues.json()["items"]
    assert len(tickets) == 1
    ticket = tickets[0]
    assert ticket["movimiento_id"] == movimiento_id
    assert ticket["proveedor"] == "Proveedor Ticket Compra"
    assert set(ticket["materiales"]) == {"Material Ticket Compra A", "Material Ticket Compra B"}
    assert ticket["folio"].startswith("C-")
    assert ticket["fecha"] == fecha_cierre


async def test_ticket_venta_se_genera_al_cerrar_movimiento_salida(client):
    material_id = await _crear_material(client, "Material Ticket Venta")
    cliente_id = await _crear_cliente(client, "Cliente Ticket Venta")
    paca_a = (await _crear_paca(client, material_id, peso=5))["id"]
    paca_b = (await _crear_paca(client, material_id, peso=7))["id"]
    movimiento_id = await _crear_movimiento(client, "SALIDA")

    await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 9.0,
            "monto_total": 63.0,
            "pacas": [paca_a, paca_b],
        },
    )

    antes = await client.get("/tickets-venta", params={"movimiento_id": movimiento_id})
    assert antes.json()["items"] == []

    cerrar = await client.patch(f"/movimientos/{movimiento_id}/cerrar")
    assert cerrar.status_code == 200
    fecha_cierre = cerrar.json()["fecha"]

    despues = await client.get("/tickets-venta", params={"movimiento_id": movimiento_id})
    tickets = despues.json()["items"]
    assert len(tickets) == 1
    ticket = tickets[0]
    assert ticket["movimiento_id"] == movimiento_id
    assert ticket["cliente"] == "Cliente Ticket Venta"
    assert ticket["cantidad_pacas"] == 2
    assert ticket["materiales"] == ["Material Ticket Venta"]
    assert ticket["folio"].startswith("V-")
    assert ticket["fecha"] == fecha_cierre


async def test_folios_de_tickets_son_unicos_entre_movimientos(client):
    material_id = await _crear_material(client, "Material Folio Unico")
    cliente_id = await _crear_cliente(client, "Cliente Folio Unico")

    folios = []
    for _ in range(2):
        paca_id = (await _crear_paca(client, material_id))["id"]
        movimiento_id = await _crear_movimiento(client, "SALIDA")
        await client.post(
            "/detalle-salida",
            json={
                "movimiento_id": movimiento_id,
                "cliente_id": cliente_id,
                "precio_venta": 5.0,
                "monto_total": 50.0,
                "pacas": [paca_id],
            },
        )
        await client.patch(f"/movimientos/{movimiento_id}/cerrar")
        ticket = (
            await client.get("/tickets-venta", params={"movimiento_id": movimiento_id})
        ).json()["items"][0]
        folios.append(ticket["folio"])

    assert len(set(folios)) == 2


async def test_ticket_venta_get_por_id(client):
    material_id = await _crear_material(client, "Material Ticket Por Id")
    cliente_id = await _crear_cliente(client, "Cliente Ticket Por Id")
    paca_id = (await _crear_paca(client, material_id))["id"]
    movimiento_id = await _crear_movimiento(client, "SALIDA")
    await client.post(
        "/detalle-salida",
        json={
            "movimiento_id": movimiento_id,
            "cliente_id": cliente_id,
            "precio_venta": 5.0,
            "monto_total": 50.0,
            "pacas": [paca_id],
        },
    )
    await client.patch(f"/movimientos/{movimiento_id}/cerrar")
    ticket = (await client.get("/tickets-venta", params={"movimiento_id": movimiento_id})).json()["items"][0]

    resp = await client.get(f"/tickets-venta/{ticket['id']}")
    assert resp.status_code == 200
    assert resp.json()["folio"] == ticket["folio"]


async def test_ticket_venta_no_encontrado_404(client):
    resp = await client.get("/tickets-venta/999999")
    assert resp.status_code == 404


async def test_ticket_compra_no_encontrado_404(client):
    resp = await client.get("/tickets-compra/999999")
    assert resp.status_code == 404
