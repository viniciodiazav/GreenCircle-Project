import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import Paginacion, ejecutar_paginado
from app.core.security import UsuarioActual, create_access_token, hash_password, verify_password
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import UsuarioCreate, UsuarioPatch

logger = logging.getLogger(__name__)

# Rate limiting de login, en memoria (dict a nivel de módulo) -- suficiente
# para un solo proceso uvicorn; se resetea si el server reinicia. Clave es
# el string de usuario tal cual lo mandó el request (aunque no exista, para
# no dejar sin límite los intentos contra cuentas inexistentes).
_INTENTOS_FALLIDOS: dict[str, list[datetime]] = {}
_MAX_INTENTOS = 5
_VENTANA = timedelta(minutes=15)


def _intentos_vigentes(usuario: str) -> list[datetime]:
    ahora = datetime.now(timezone.utc)
    vigentes = [t for t in _INTENTOS_FALLIDOS.get(usuario, []) if ahora - t < _VENTANA]
    _INTENTOS_FALLIDOS[usuario] = vigentes
    return vigentes


def _registrar_intento_fallido(usuario: str) -> None:
    vigentes = _intentos_vigentes(usuario)
    vigentes.append(datetime.now(timezone.utc))
    _INTENTOS_FALLIDOS[usuario] = vigentes


async def autenticar_usuario(usuario: str, password: str, db: AsyncSession) -> str:
    if len(_intentos_vigentes(usuario)) >= _MAX_INTENTOS:
        logger.warning("Login bloqueado por rate-limit: usuario=%r", usuario)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Intenta de nuevo en unos minutos.",
        )

    result = await db.execute(select(Usuario).where(Usuario.usuario == usuario))
    fila = result.scalar_one_or_none()

    if fila is None or not fila.activo or not verify_password(password, fila.password_hash):
        _registrar_intento_fallido(usuario)
        logger.warning("Login fallido: usuario=%r", usuario)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    _INTENTOS_FALLIDOS.pop(usuario, None)
    logger.info("Login exitoso: usuario=%r id=%s", fila.usuario, fila.id)
    return create_access_token(subject=fila.usuario, usuario_id=fila.id)


async def listar_usuarios(db: AsyncSession, paginacion: Paginacion) -> tuple[list[Usuario], int]:
    stmt = select(Usuario).order_by(Usuario.usuario)
    return await ejecutar_paginado(stmt, db, paginacion)


async def crear_usuario(data: UsuarioCreate, db: AsyncSession, actor: UsuarioActual) -> Usuario:
    usuario = Usuario(usuario=data.usuario, password_hash=hash_password(data.password))
    db.add(usuario)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ese usuario ya existe")
    await db.refresh(usuario)
    logger.info(
        "Usuario creado: usuario=%r id=%s por actor=%r id=%s",
        usuario.usuario, usuario.id, actor.usuario, actor.id,
    )
    return usuario


async def get_usuario_or_404(usuario_id: int, db: AsyncSession) -> Usuario:
    usuario = await db.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario


async def actualizar_usuario(
    usuario_id: int, data: UsuarioPatch, db: AsyncSession, actor: UsuarioActual
) -> Usuario:
    if data.activo is None and data.password is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar activo y/o password",
        )
    usuario = await get_usuario_or_404(usuario_id, db)
    if data.activo is not None:
        usuario.activo = data.activo
        logger.info(
            "Usuario %r id=%s activo=%s por actor=%r id=%s",
            usuario.usuario, usuario.id, data.activo, actor.usuario, actor.id,
        )
    if data.password is not None:
        usuario.password_hash = hash_password(data.password)
        logger.info(
            "Password cambiado: usuario=%r id=%s por actor=%r id=%s",
            usuario.usuario, usuario.id, actor.usuario, actor.id,
        )
    await db.commit()
    await db.refresh(usuario)
    return usuario
