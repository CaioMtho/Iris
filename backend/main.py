from fastapi import FastAPI
from backend.api.routers import politicos

app = FastAPI()

app.include_router(politicos.router, prefix="/politicos", tags=["politicos"])
@app.get("/")
async def root():
    """Rota raiz de status"""
    return {"message": "IRIS rodando!"}
