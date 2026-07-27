async def test_crear_usuario(client):
    resp = await client.post("/usuarios", json={"usuario": "nuevo_usuario", "password": "clave12345"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["usuario"] == "nuevo_usuario"
    assert data["activo"] is True
    assert "password" not in data
    assert "password_hash" not in data


async def test_crear_usuario_duplicado_409(client, usuario_test):
    resp = await client.post(
        "/usuarios", json={"usuario": usuario_test.usuario, "password": "clave12345"}
    )
    assert resp.status_code == 409


async def test_crear_usuario_password_corta_422(client):
    resp = await client.post("/usuarios", json={"usuario": "usuario_x", "password": "corta"})
    assert resp.status_code == 422


async def test_get_usuarios_lista(client, usuario_test):
    resp = await client.get("/usuarios")
    assert resp.status_code == 200
    usuarios = [item["usuario"] for item in resp.json()["items"]]
    assert usuario_test.usuario in usuarios


async def test_get_usuario_no_encontrado_404(client):
    resp = await client.get("/usuarios/999999")
    assert resp.status_code == 404


async def test_patch_usuario_desactivar(client, usuario_test):
    resp = await client.patch(f"/usuarios/{usuario_test.id}", json={"activo": False})
    assert resp.status_code == 200
    assert resp.json()["activo"] is False


async def test_patch_usuario_sin_campos_400(client, usuario_test):
    resp = await client.patch(f"/usuarios/{usuario_test.id}", json={})
    assert resp.status_code == 400


async def test_patch_usuario_cambia_password_y_permite_login(client, client_sin_auth, usuario_test):
    resp = await client.patch(f"/usuarios/{usuario_test.id}", json={"password": "nueva-clave-123"})
    assert resp.status_code == 200

    login_resp = await client_sin_auth.post(
        "/auth/login", json={"usuario": usuario_test.usuario, "password": "nueva-clave-123"}
    )
    assert login_resp.status_code == 200


async def test_usuario_desactivado_no_puede_loguear(client, client_sin_auth, usuario_test):
    await client.patch(f"/usuarios/{usuario_test.id}", json={"activo": False})

    login_resp = await client_sin_auth.post(
        "/auth/login", json={"usuario": usuario_test.usuario, "password": "clave-prueba"}
    )
    assert login_resp.status_code == 401
