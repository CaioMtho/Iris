from fastapi import FastAPI
from backend.api.routers import politicos_routes, prototipo_routes
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Servidor da Iris")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(politicos_routes.router, prefix="/api/v1")
app.include_router(prototipo_routes.router, prefix="/api/v1")

app.mount("/", StaticFiles(directory="backend/static", html=True), name="static")
