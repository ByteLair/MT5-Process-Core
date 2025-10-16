#!/bin/bash
set -euo pipefail

# Log file setup
LOG_DIR="/var/log/mt5"
LOG_FILE="$LOG_DIR/db_maintenance.log"
mkdir -p "$LOG_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting database maintenance tasks..."

# Run VACUUM ANALYZE
log "Running VACUUM ANALYZE..."
docker exec mt5_db psql -U trader -d mt5_trading -c 'VACUUM (ANALYZE, VERBOSE);' >> "$LOG_FILE" 2>&1

# Check and compress chunks older than 30 days
log "Compressing old chunks..."
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT compress_chunk(i, if_not_compressed => true) 
FROM show_chunks('market_data', older_than => INTERVAL '30 days') i;" >> "$LOG_FILE" 2>&1

# Remove chunks older than 5 years
log "Removing chunks older than 5 years..."
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT drop_chunks('market_data', older_than => INTERVAL '5 years');" >> "$LOG_FILE" 2>&1

# Update statistics
log "Updating database statistics..."
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT _timescaledb_functions.update_chunk_statistics(i)
FROM show_chunks('market_data') i;" >> "$LOG_FILE" 2>&1

# Check compression status
log "Current compression status:"
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT 
    hypertable_name,
    pg_size_pretty(total_bytes) as total_size,
    pg_size_pretty(total_compressed_bytes) as compressed_size,
    round(compression_ratio::numeric, 2) as compression_ratio
FROM timescaledb_information.hypertable_compression_stats;" >> "$LOG_FILE" 2>&1

log "Database maintenance completed successfully"