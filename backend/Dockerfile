# Dockerfile — Backend (FastAPI)
# Build context agora e' a RAIZ do projeto (nexusflow/), nao mais backend/.
# Motivo: padronizar import em backend.app.X tanto pro Alembic (host, roda
# da raiz) quanto pro container -- antes so' backend/ era montado como /app,
# entao "backend.app.X" nao existia dentro do container. Ver docker-compose.yml.
#
# Alembic/alembic.ini agora vao junto no COPY . . (nao precisa mais de volume
# separado nem de ajuste especial de contexto no build de producao/Railway).

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]