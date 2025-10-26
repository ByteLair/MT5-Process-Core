#!/usr/bin/env bash
# Adjust PostgreSQL memory settings based on total system RAM
set -euo pipefail

CONF_FILE="/home/felipe/mt5-trading-db/docker/postgres.conf.d/postgresql.conf"
TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
TOTAL_RAM_GB=$((TOTAL_RAM_KB / 1024 / 1024))

# Calculate 25% of RAM for shared_buffers (minimum 1GB)
SHARED_BUFFERS_GB=$((TOTAL_RAM_GB / 4))
if [ "$SHARED_BUFFERS_GB" -lt 1 ]; then
    SHARED_BUFFERS_GB=1
fi

# Calculate 50% of RAM for effective_cache_size (minimum 2GB)
EFFECTIVE_CACHE_GB=$((TOTAL_RAM_GB / 2))
if [ "$EFFECTIVE_CACHE_GB" -lt 2 ]; then
    EFFECTIVE_CACHE_GB=2
fi

echo "Adjusting PostgreSQL memory settings based on ${TOTAL_RAM_GB}GB total RAM:"
echo "  shared_buffers = ${SHARED_BUFFERS_GB}GB"
echo "  effective_cache_size = ${EFFECTIVE_CACHE_GB}GB"

# Update the postgresql.conf file
sed -i.bak \
    -e "s/shared_buffers = '1GB'/shared_buffers = '${SHARED_BUFFERS_GB}GB'/" \
    -e "s/effective_cache_size = '3GB'/effective_cache_size = '${EFFECTIVE_CACHE_GB}GB'/" \
    "$CONF_FILE"

echo "Updated $CONF_FILE"
echo "Backup saved as ${CONF_FILE}.bak"
echo
echo "To apply changes:"
echo "1. Verify the changes: diff ${CONF_FILE}.bak $CONF_FILE"
echo "2. Restart the database: docker-compose restart db"
