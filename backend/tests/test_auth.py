import bcrypt

from app.modules.auth.models import Admin


async def test_login_ok(client, db_session):
    password_hash = bcrypt.hashpw(b"clave-prueba-123", bcrypt.gensalt()).decode()
    db_session.add(Admin(usuario="admin_prueba", password_hash=password_hash))
    await db_session.commit()

    resp = await client.post(
        "/auth/login", json={"usuario": "admin_prueba", "password": "clave-prueba-123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


async def test_login_password_incorrecta_401(client, db_session):
    password_hash = bcrypt.hashpw(b"clave-correcta", bcrypt.gensalt()).decode()
    db_session.add(Admin(usuario="admin_prueba_2", password_hash=password_hash))
    await db_session.commit()

    resp = await client.post(
        "/auth/login", json={"usuario": "admin_prueba_2", "password": "clave-incorrecta"}
    )
    assert resp.status_code == 401


async def test_login_usuario_inexistente_401(client):
    resp = await client.post("/auth/login", json={"usuario": "no_existe", "password": "x"})
    assert resp.status_code == 401
