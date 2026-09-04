from fastapi import FastAPI

from backend.app.api.routes import auth_route

app = FastAPI(title="Painel Executivo — Outorgas de Geração")

app.include_router(auth_route.router)


@app.get("/health")
def health():
    return {"status": "ok"}