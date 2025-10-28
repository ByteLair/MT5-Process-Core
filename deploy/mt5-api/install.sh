#!/bin/bash
set -euo pipefail

DB_NAME="mt5_data"
DB_USER="mt5user"
DB_PASSWORD="[GENERATE_OR_SET]"
API_PORT=8000
ALLOWED_IP="192.168.15.19"
APP_DIR="/opt/mt5-api"

if [ "$EUID" -ne 0 ]; then
  echo "Run as root"
  exit 2
fi

apt update
apt -y upgrade
apt -y install wget ca-certificates gnupg lsb-release software-properties-common curl python3 python3-venv python3-pip openssl

# Install PostgreSQL 15
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg || true
echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list
apt update
apt -y install postgresql-15 postgresql-client-15 postgresql-contrib

# TimescaleDB
wget -qO- https://apt.timescale.com/api/gpg/key/public | gpg --dearmor -o /usr/share/keyrings/timescale.gpg || true
echo "deb [signed-by=/usr/share/keyrings/timescale.gpg] https://apt.timescale.com/ubuntu $(lsb_release -cs) main" > /etc/apt/sources.list.d/timescale.list
apt update
apt -y install timescaledb-2-postgresql-15
timescaledb-tune --quiet --yes || true
systemctl restart postgresql

# Create DB and user
if [ "$DB_PASSWORD" = "[GENERATE_OR_SET]" ]; then
  DB_PASSWORD=$(openssl rand -base64 24)
  echo "$DB_PASSWORD" > /root/.mt5_db_password
  chmod 600 /root/.mt5_db_password
fi

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO

\$do\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
      CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';
   ELSE
      ALTER ROLE ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
   END IF;
END
\$do\$;

CREATE DATABASE ${DB_NAME};
ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};
SQL

# Apply schema (assuming deploy dir)
mkdir -p "$APP_DIR"
cp deploy/mt5-api/schema.sql "$APP_DIR/" || true
sudo -u postgres psql -d "$DB_NAME" -f "$APP_DIR/schema.sql"

# Create system user
id -u mt5api >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin mt5api
chown mt5api:mt5api "$APP_DIR"

# Setup venv and app
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r deploy/mt5-api/requirements.txt
cp deploy/mt5-api/api.py "$APP_DIR/api.py"
cp deploy/mt5-api/.env "$APP_DIR/.env"
chown -R mt5api:mt5api "$APP_DIR"

# Create log file
mkdir -p /var/log
touch /var/log/mt5_api.log
chown mt5api:mt5api /var/log/mt5_api.log

# Systemd service
cat > /etc/systemd/system/mt5-api.service <<SERVICE
[Unit]
Description=MT5 Ingest API (FastAPI + Uvicorn)
After=network.target

[Service]
Type=simple
User=mt5api
Group=mt5api
WorkingDirectory=/opt/mt5-api
Environment="PATH=/opt/mt5-api/venv/bin"
EnvironmentFile=-/opt/mt5-api/.env
ExecStart=/opt/mt5-api/venv/bin/uvicorn api:app --host 0.0.0.0 --port ${API_PORT} --workers 1
Restart=on-failure
RestartSec=5s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable mt5-api.service
systemctl restart mt5-api.service

# Configure UFW
apt -y install ufw
ufw --force reset
ufw allow 22/tcp
ufw allow from ${ALLOWED_IP} to any port ${API_PORT} proto tcp
ufw allow from 127.0.0.1 to any port 5432 proto tcp
ufw default deny incoming
ufw default allow outgoing
ufw --force enable

echo "Installation complete. DB_PASSWORD stored in /root/.mt5_db_password if generated."
