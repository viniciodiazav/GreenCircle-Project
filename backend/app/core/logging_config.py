import logging
import logging.handlers
from pathlib import Path

# backend/logs/ -- junto al proyecto, no dentro de app/. No se versiona
# (ver .gitignore); en Docker vive dentro del contenedor a menos que se
# monte un volumen (el `docker-compose.yml` ya monta ./backend completo).
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"


def configurar_logging() -> None:
    """Consola (stdout, para `docker compose logs` o la terminal) + archivo
    rotativo (para que sobreviva a cerrar la terminal o reiniciar el
    contenedor). Se cuelga del logger "app" -- todos los loggers del
    proyecto usan `logging.getLogger(__name__)` bajo el paquete `app`, así
    que propagan hacia acá sin configurar nada más por módulo."""
    LOG_DIR.mkdir(exist_ok=True)
    formato = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    consola = logging.StreamHandler()
    consola.setFormatter(formato)

    archivo = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    archivo.setFormatter(formato)

    logger_app = logging.getLogger("app")
    logger_app.setLevel(logging.INFO)
    logger_app.addHandler(consola)
    logger_app.addHandler(archivo)
