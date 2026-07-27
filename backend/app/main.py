import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.logging_config import configurar_logging
from app.modules.ajustes_inventario.router import router as ajustes_inventario_router
from app.modules.auth.router import router as auth_router
from app.modules.auth.router import usuarios_router
from app.modules.clientes.router import router as clientes_router
from app.modules.detalle_entrada.router import router as detalle_entrada_router
from app.modules.detalle_salida.router import router as detalle_salida_router
from app.modules.historial_kg.router import router as historial_kg_router
from app.modules.historial_pacas.router import router as historial_pacas_router
from app.modules.historial_precios.router import router as historial_precios_router
from app.modules.inventario.router import router as inventario_router
from app.modules.materiales.router import router as materiales_router
from app.modules.movimientos.router import router as movimientos_router
from app.modules.pacas.router import router as pacas_router
from app.modules.proveedores.router import router as proveedores_router
from app.modules.tickets_compra.router import router as tickets_compra_router
from app.modules.tickets_venta.router import router as tickets_venta_router

configurar_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Centro de Recolección - API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def manejador_error_no_controlado(request: Request, exc: Exception) -> JSONResponse:
    """Red de seguridad para cualquier excepción que no sea un HTTPException
    (esas ya las maneja FastAPI con su propio handler, más específico, que
    gana en la búsqueda por MRO antes de llegar aquí). Sin esto, un 500 no
    dejaba ningún rastro más allá de lo que uvicorn imprime mientras el
    proceso sigue corriendo."""
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(materiales_router)
app.include_router(proveedores_router)
app.include_router(clientes_router)
app.include_router(movimientos_router)
app.include_router(detalle_entrada_router)
app.include_router(detalle_salida_router)
app.include_router(pacas_router)
app.include_router(inventario_router)
app.include_router(historial_precios_router)
app.include_router(historial_kg_router)
app.include_router(historial_pacas_router)
app.include_router(ajustes_inventario_router)
app.include_router(tickets_venta_router)
app.include_router(tickets_compra_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
