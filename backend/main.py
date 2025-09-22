from fastapi import FastAPI
from backend.api.routers import politicos_routes, prototipo_routes

app = FastAPI(title="Servidor da Iris")

app.include_router(politicos_routes.router, prefix="/api/v1")
app.include_router(prototipo_routes.router, prefix="/api/v1")
