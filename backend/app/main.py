from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.auth.router import router as auth_router
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

app = FastAPI(title="Centro de Recolección - API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
