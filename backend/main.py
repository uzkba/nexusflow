from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import auth_route, consolidacoes_route, projetos_route, dashboard_route, geolocalizacao_route

app = FastAPI(title="Painel Executivo — Outorgas de Geração")

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

app.include_router(auth_route.router)
app.include_router(consolidacoes_route.router)
app.include_router(geolocalizacao_route.router)
app.include_router(projetos_route.router)
app.include_router(dashboard_route.router)

@app.get("/health")
def health():
    return {"status": "ok"}