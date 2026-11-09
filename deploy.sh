#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/uzkba/nexusflow"
BRANCH="deploy-nexusflow"
SERVICES="backend frontend"

main() {
  cd "$APP_DIR"

  echo "==> $(date) Atualizando código ($BRANCH)"
  git fetch origin "$BRANCH"
  git checkout "$BRANCH"
  git reset --hard "origin/$BRANCH"

  echo "==> Build dos containers"
  docker compose build $SERVICES

  echo "==> Subindo containers"
  docker compose up -d --no-deps $SERVICES

  echo "==> Migrations"
  docker compose exec -T backend alembic upgrade head

  echo "==> Limpeza de imagens antigas"
  docker image prune -f

  echo "==> $(date) Deploy concluído"
}

main "$@"
exit 0
