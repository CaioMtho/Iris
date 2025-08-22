from fastapi import FastAPI
from backend.api.routers import politicos_routes

app = FastAPI()

app.include_router(politicos_routes.router, prefix="/api/v1")

@app.get("/")
async def root():
    """Rota raiz"""
    return {"message": "IRIS rodando!"}
