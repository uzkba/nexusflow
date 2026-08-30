from fastapi import FastAPI

app = FastAPI(title="Painel Executivo — Outorgas de Geração")


@app.get("/health")
def health():
    return {"status": "ok"}