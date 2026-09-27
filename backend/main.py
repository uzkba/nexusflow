from fastapi import FastAPI

from backend.app.api.routes import auth_route, consolidacoes_route, dashboard_route

app = FastAPI(title="Painel Executivo — Outorgas de Geração")

app.include_router(auth_route.router)
app.include_router(consolidacoes_route.router)
app.include_router(dashboard_route.router)  # 🔧 AJUSTE ESTA LINHA: caminho real do seu dashboard_route.py

# Próximos routers (kpis, projetos, graficos, geolocalizacao) já nascem
# protegidos via dependencies=[Depends(get_current_user)] no próprio
# APIRouter — ver backend/app/core/auth_dependencies.py.
# Ex.: app.include_router(kpis_route.router)


@app.get("/health")
def health():
    return {"status": "ok"}