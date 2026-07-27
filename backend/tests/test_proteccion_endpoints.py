async def test_get_materiales_publico_sin_token_200(client_sin_auth):
    """GET /materiales es el único listado público -- lo usa la app móvil
    sin login (ver app-movil/src/screens/HomeScreen.tsx)."""
    resp = await client_sin_auth.get("/materiales")
    assert resp.status_code == 200


async def test_get_materiales_admin_sin_token_401(client_sin_auth):
    resp = await client_sin_auth.get("/materiales/admin")
    assert resp.status_code == 401


async def test_post_movimiento_sin_token_401(client_sin_auth):
    resp = await client_sin_auth.post("/movimientos", json={"tipo": "ENTRADA"})
    assert resp.status_code == 401


async def test_get_movimientos_con_token_200(client):
    resp = await client.get("/movimientos")
    assert resp.status_code == 200
