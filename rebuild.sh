#!/bin/bash
set -e

COMPOSE="docker compose -f docker-compose.deploy.yml"

git pull

# контейнер работает от владельца базы, чтобы писать в неё (см. Dockerfile)
export APP_UID=$(stat -c %u app/db.sqlite3)
# сборка до остановки: если она упадёт, старый контейнер продолжит работать
$COMPOSE build
$COMPOSE down --remove-orphans
$COMPOSE up -d
