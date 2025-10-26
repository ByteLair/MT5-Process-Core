#!/usr/bin/env bash
set -euo pipefail
# Fix permissions for host directories used as bind mounts in docker-compose
# Reads UID/GID from .env if present, otherwise from current user
ENV_FILE="$(pwd)/.env"
MY_UID=""
MY_GID=""
if [[ -f "$ENV_FILE" ]]; then
  UID_LINE=$(grep -E '^UID=' "$ENV_FILE" || true)
  GID_LINE=$(grep -E '^GID=' "$ENV_FILE" || true)
  if [[ -n "$UID_LINE" ]]; then
    MY_UID=$(echo "$UID_LINE" | cut -d'=' -f2)
  fi
  if [[ -n "$GID_LINE" ]]; then
    MY_GID=$(echo "$GID_LINE" | cut -d'=' -f2)
  fi
fi
if [[ -z "$MY_UID" ]]; then
  MY_UID=$(id -u)
fi
if [[ -z "$MY_GID" ]]; then
  MY_GID=$(id -g)
fi
echo "Using UID=$MY_UID GID=$MY_GID"
# List of host paths (relative to repo root)
HOST_PATHS=(
  "db/init"
  "docker/postgres.conf.d"
  "scripts"
  "api/logs"
  "api/data_raw"
  "ml/data"
  "grafana/provisioning"
  "loki"
  "prometheus.yml"
  "logs"
)
# Create directories and set ownership
for p in "${HOST_PATHS[@]}"; do
  # if ends with .yml treat as file's parent dir
  if [[ "$p" == *.yml ]]; then
    dir=$(dirname "$p")
    mkdir -p "$dir"
    touch "$p" || true
    chown -R "$MY_UID:$MY_GID" "$dir" || true
    chmod -R 775 "$dir" || true
    echo "Ensured file and permissions: $p"
  else
    mkdir -p "$p"
    chown -R "$MY_UID:$MY_GID" "$p" || true
    chmod -R 775 "$p" || true
    echo "Ensured dir and permissions: $p"
  fi
done
# Create named volumes that are referenced as external in docker-compose
VOLUMES=("models_mt5")
for v in "${VOLUMES[@]}"; do
  if ! sudo docker volume inspect "$v" >/dev/null 2>&1; then
    echo "Creating docker volume: $v"
    sudo docker volume create "$v" >/dev/null
  else
    echo "Docker volume exists: $v"
  fi
done

echo "Permissions fix complete."