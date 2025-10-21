#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: restore.sh <dump_file>"
  exit 1
fi

DUMP="$1"
DB=${POSTGRES_DB:-mt5_trading}
USER=${POSTGRES_USER:-trader}
HOST=${POSTGRES_HOST:-localhost}
PORT=${POSTGRES_PORT:-5432}

export PGPASSWORD="${POSTGRES_PASSWORD:-trader123}"
dropdb  -h "$HOST" -p "$PORT" -U "$USER" --if-exists "$DB"
createdb -h "$HOST" -p "$PORT" -U "$USER" "$DB"
pg_restore -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" --clean --if-exists "$DUMP"
echo "Restore completed into DB: $DB"
