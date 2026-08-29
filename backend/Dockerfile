# Dockerfile — Backend (FastAPI)
# Alembic fica na raiz do projeto (fora desta pasta) e é montado via volume
# em desenvolvimento (ver docker-compose.yml). Em produção, o alembic.ini
# e a pasta alembic/ precisam ser copiados também (ver comentário abaixo).

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Em build de produção (Railway), o contexto precisa incluir alembic/ e
# alembic.ini da raiz do repo — ajustar build context no railway.json
# quando chegar nessa etapa, já que localmente isso é resolvido via volume.

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]