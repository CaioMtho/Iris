from fastapi import FastAPI
from backend.api.routers import politicos_routes

app = FastAPI(title="Servidor da Iris")

app.include_router(politicos_routes.router, prefix="/api/v1")
