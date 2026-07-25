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


async def _crear_paca(client, material_id, peso=10):
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
        },
    )
    assert resp.status_code == 409


async def test_detalle_entrada_movimiento_cerrado_409(client):
    proveedor_id = await _crear_proveedor(client, "Proveedor Entrada C")
    material_id = await _crear_material(client, "Material Entrada C")
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
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
        },
    )
    assert resp.status_code == 201

    inventario = await client.get("/inventario")
    fila = next(f for f in inventario.json() if f["material_id"] == material_id)
    assert fila["peso_total"] == 70.0

    historial = await client.get("/historial-kg", params={"material_id": material_id})
    filas = historial.json()
    assert len(filas) == 1
    assert filas[0]["peso_anterior"] == 0.0
    assert filas[0]["peso_nuevo"] == 70.0


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
    filas = historial.json()
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
    fila = next(f for f in inventario_pacas.json() if f["material_id"] == material_id)
    assert fila["cantidad"] == 0

    historial = await client.get("/historial-pacas", params={"paca_id": paca_id})
    eventos = {f["evento"] for f in historial.json()}
    assert eventos == {"ALTA", "VENTA"}

    detalle_salida_get = await client.get("/detalle-salida", params={"movimiento_id": movimiento_id})
    assert detalle_salida_get.json()[0]["cantidad_pacas"] == 1


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
            "pacas": [paca_id],
        },
    )
    assert resp.status_code == 400


async def test_cerrar_movimiento_dos_veces_409(client):
    movimiento_id = await _crear_movimiento(client, "ENTRADA")
    r1 = await client.patch(f"/movimientos/{movimiento_id}/cerrar")
    assert r1.status_code == 200
    assert r1.json()["cerrado"] is True
    r2 = await client.patch(f"/movimientos/{movimiento_id}/cerrar")
    assert r2.status_code == 409


async def test_listar_movimientos_filtra_por_tipo(client):
    entrada_id = await _crear_movimiento(client, "ENTRADA")
    salida_id = await _crear_movimiento(client, "SALIDA")

    entradas = await client.get("/movimientos", params={"tipo": "ENTRADA"})
    ids_entrada = [m["id"] for m in entradas.json()]
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
            "pacas": [paca_id],
        },
    )
    assert resp.status_code == 409


async def test_registrar_paca_material_inactivo_409(client):
    material_id = await _crear_material(client, "Material Inactivo Paca")
    await client.patch(f"/materiales/{material_id}", json={"activo": False})

    resp = await client.post("/pacas", json={"material_id": material_id, "peso": 10})
    assert resp.status_code == 409
