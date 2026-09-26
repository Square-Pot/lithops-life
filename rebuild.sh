#!/bin/bash
set -e

COMPOSE="docker compose -f docker-compose.deploy.yml"

git pull
$COMPOSE down --remove-orphans
$COMPOSE up -d --build
