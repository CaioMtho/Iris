from fastapi import FastAPI, APIRouter
from backend.api.routers import dados_questionario_routes, politicos_routes, prototipo_routes, chat_routes
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Servidor da Iris")
router = APIRouter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(politicos_routes.router, prefix="/api/v1")
app.include_router(prototipo_routes.router, prefix="/api/v1")
app.include_router(chat_routes.router, prefix="/api/v1")
app.include_router(dados_questionario_routes.router, prefix="/api/v1", tags=["dados de questionarios"])
app.mount("/", StaticFiles(directory="backend/static", html=True), name="static")