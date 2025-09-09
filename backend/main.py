from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from backend.api.routers import politicos_routes
from backend.services.ingest_service import ingest_zip
from contextlib import asynccontextmanager
import torch

app = FastAPI(title="Servidor da Iris")


@asynccontextmanager
async def lifespan():
    '''Carrega o modelo de embeddings na inicialização'''
    num_threads = int(__import__("os").environ.get("OMP_NUM_THREADS", "4"))
    torch.set_num_threads(num_threads)
    torch.set_num_interop_threads(num_threads)
    yield

app.include_router(politicos_routes.router, prefix="/api/v1")

@app.post("/api/v1/ingestao/lote")
async def ingest_lote(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    '''Ingestão de um lote de dados a partir de um arquivo zip.'''
    if background_tasks:
        background_tasks.add_task(ingest_zip, file)
        return {"status": "accepted"}
    result = await ingest_zip(file)
    return {"status": "ok", "result": result}