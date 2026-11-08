from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Adjust import paths based on your actual project structure
from backend.app.core.scheduler import setup_scheduler, shutdown_scheduler

from backend.app.api.routes import (
    auth_route, 
    consolidacoes_route, 
    projetos_route, 
    dashboard_route, 
    geolocalizacao_route,
    etl_runs_route
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown events securely.
    """
    logger.info("Starting up NexusFlow API and background scheduler...")
    setup_scheduler()
    
    yield  # The FastAPI application handles requests here
    
    logger.info("Shutting down NexusFlow API and stopping scheduler...")
    shutdown_scheduler()


app = FastAPI(
    title="Painel Executivo — Outorgas de Geração",
    lifespan=lifespan  # <-- Lifespan injected here
)

# 🌐 Configuração de CORS atualizada para cobrir localhost e 127.0.0.1
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost"
    ],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# Registro das rotas da API
app.include_router(auth_route.router)
app.include_router(consolidacoes_route.router)
app.include_router(geolocalizacao_route.router)
app.include_router(projetos_route.router)
app.include_router(dashboard_route.router)
app.include_router(etl_runs_route.router)

@app.get("/health")
def health():
    return {"status": "ok"}