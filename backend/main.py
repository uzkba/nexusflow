from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import auth_route, consolidacoes_route, projetos_route, dashboard_route, geolocalizacao_route

app = FastAPI(title="Painel Executivo — Outorgas de Geração")

# 🌐 Configuração de CORS para permitir a comunicação com o Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Permite o frontend rodando no Vite
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],  # Permite todos os cabeçalhos (inclusive Authorization/Bearer tokens)
)

app.include_router(auth_route.router)
app.include_router(consolidacoes_route.router)
app.include_router(geolocalizacao_route.router)
app.include_router(projetos_route.router)
app.include_router(dashboard_route.router)  # 🔧 AJUSTE ESTA LINHA: caminho real do seu dashboard_route.py

# Próximos routers (kpis, projetos, graficos, geolocalizacao) já nascem
# protegidos via dependencies=[Depends(get_current_user)] no próprio
# APIRouter — ver backend/app/core/auth_dependencies.py.
# Ex.: app.include_router(kpis_route.router)


@app.get("/health")
def health():
    return {"status": "ok"}