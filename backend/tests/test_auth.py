import bcrypt

from app.modules.auth.models import Usuario


async def test_login_ok(client, db_session):
    password_hash = bcrypt.hashpw(b"clave-prueba-123", bcrypt.gensalt()).decode()
    db_session.add(Usuario(usuario="usuario_prueba_login", password_hash=password_hash))
    await db_session.commit()

    resp = await client.post(
        "/auth/login", json={"usuario": "usuario_prueba_login", "password": "clave-prueba-123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


async def test_login_password_incorrecta_401(client, db_session):
    password_hash = bcrypt.hashpw(b"clave-correcta", bcrypt.gensalt()).decode()
    db_session.add(Usuario(usuario="usuario_prueba_2", password_hash=password_hash))
    await db_session.commit()

    resp = await client.post(
        "/auth/login", json={"usuario": "usuario_prueba_2", "password": "clave-incorrecta"}
    )
    assert resp.status_code == 401


async def test_login_usuario_inexistente_401(client):
    resp = await client.post("/auth/login", json={"usuario": "no_existe", "password": "x"})
    assert resp.status_code == 401


async def test_login_usuario_inactivo_401(client, db_session):
    password_hash = bcrypt.hashpw(b"clave-correcta", bcrypt.gensalt()).decode()
    db_session.add(
        Usuario(usuario="usuario_dado_de_baja", password_hash=password_hash, activo=False)
    )
    await db_session.commit()

    resp = await client.post(
        "/auth/login", json={"usuario": "usuario_dado_de_baja", "password": "clave-correcta"}
    )
    assert resp.status_code == 401


async def test_login_bloqueado_tras_intentos_fallidos_429(client):
    """El rate-limit vive en un dict a nivel de módulo -- usuario único para
    no interferir con otros tests que corran en el mismo proceso."""
    for _ in range(5):
        resp = await client.post(
            "/auth/login",
            json={"usuario": "usuario_rate_limit_test", "password": "incorrecta"},
        )
        assert resp.status_code == 401

    resp = await client.post(
        "/auth/login",
        json={"usuario": "usuario_rate_limit_test", "password": "incorrecta"},
    )
    assert resp.status_code == 429
