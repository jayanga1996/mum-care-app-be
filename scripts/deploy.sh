#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh – Zero-downtime deploy script for AWS EC2
#
# Usage:
#   bash scripts/deploy.sh
#
# Prerequisites on the EC2 instance:
#   - Docker & Docker Compose installed
#   - .env file present in /home/ubuntu/MUM_CARE_APP_BE/
#   - SSH key-based access
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="/home/ubuntu/MUM_CARE_APP_BE"
IMAGE_NAME="mum_care_backend"

echo "==> Pulling latest code..."
cd "$APP_DIR"
git pull origin main

echo "==> Building Docker image..."
docker compose build --no-cache web

echo "==> Applying database migrations..."
docker compose run --rm web python manage.py migrate --noinput

echo "==> Collecting static files..."
docker compose run --rm web python manage.py collectstatic --noinput

echo "==> Seeding reference data (idempotent)..."
docker compose run --rm web python manage.py seed_data

echo "==> Restarting services..."
docker compose up -d --force-recreate web celery nginx

echo "==> Cleaning up old images..."
docker image prune -f

echo "✅  Deployment complete!"
