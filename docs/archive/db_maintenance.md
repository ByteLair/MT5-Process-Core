# Database Maintenance Guide

## Automated Maintenance Tasks

### Daily Tasks (3:00 AM)

- Docker system cleanup (`docker system prune -f`)
- TimescaleDB retention policy execution
- Automatic compression of old chunks

### Weekly Tasks (Sunday 4:15 AM)

The maintenance script `/home/felipe/mt5-trading-db/scripts/db_maintenance.sh` performs:

- Full VACUUM ANALYZE
- Compression of chunks older than 30 days
- Cleanup of chunks older than 5 years
- Update of chunk statistics
- Generation of compression status report

## TimescaleDB Policies

### Current Configuration

```sql
-- Compression Policy
Schedule: Every 12 hours
Data older than: 7 days
Compression settings:
  - Segment by: symbol
  - Order by: timestamp

-- Reorder Policy
Schedule: Every 12 hours
Index: ux_market_data_sym_tf_ts

-- Retention Policy
Schedule: Daily
Retention period: 90 days
```

### Monitoring Policies

To check policy status:

```sql
SELECT * FROM timescaledb_information.jobs
WHERE hypertable_name = 'market_data';
```

### Compression Status

View current compression metrics:

```sql
SELECT
    hypertable_name,
    pg_size_pretty(total_bytes) as total_size,
    pg_size_pretty(total_compressed_bytes) as compressed_size,
    round(compression_ratio::numeric, 2) as compression_ratio
FROM timescaledb_information.hypertable_compression_stats;
```

## Manual Maintenance & Monitoring

### Examples of Common Tasks

#### 1. Compress Specific Symbol Data

```sql
-- Compress all EURUSD data older than 15 days
SELECT compress_chunk(i, if_not_compressed => true)
FROM show_chunks(
    'market_data',
    older_than => INTERVAL '15 days'
) i
WHERE i IN (
    SELECT chunk_name
    FROM timescaledb_information.chunks
    WHERE hypertable_name = 'market_data'
    AND min_value::json->>'symbol' = 'EURUSD'
);
```

#### 2. Check Data Distribution

```sql
-- Data volume by symbol and timeframe
SELECT
    symbol,
    timeframe,
    count(*) as records,
    pg_size_pretty(sum(pg_column_size(market_data))*1.0) as data_size,
    min(timestamp) as oldest_record,
    max(timestamp) as newest_record
FROM market_data
GROUP BY symbol, timeframe
ORDER BY records DESC;
```

#### 3. Identify Uncompressed Chunks

```sql
-- Find chunks that should be compressed but aren't
WITH chunk_status AS (
    SELECT
        chunk_name,
        range_start,
        range_end,
        is_compressed
    FROM timescaledb_information.chunks
    WHERE hypertable_name = 'market_data'
)
SELECT
    chunk_name,
    range_start,
    range_end,
    pg_size_pretty(pg_relation_size(chunk_name::regclass)) as chunk_size
FROM chunk_status
WHERE NOT is_compressed
AND range_end < now() - INTERVAL '30 days'
ORDER BY range_start;
```

#### 4. Monitor Chunk Distribution

```sql
-- Show chunk sizes and compression ratios
SELECT
    chunk_name,
    pg_size_pretty(before_compression_total_bytes) as original_size,
    pg_size_pretty(after_compression_total_bytes) as compressed_size,
    round(100 - (after_compression_total_bytes::numeric /
                 before_compression_total_bytes::numeric * 100), 2) as compression_pct
FROM timescaledb_information.compression_chunk_size
ORDER BY before_compression_total_bytes DESC
LIMIT 10;
```

### Advanced Maintenance Tasks

#### 1. Recompress Inefficient Chunks

```sql
-- Find and recompress chunks with poor compression ratios
WITH compression_stats AS (
    SELECT
        chunk_name,
        before_compression_total_bytes,
        after_compression_total_bytes,
        round(100 - (after_compression_total_bytes::numeric /
                     before_compression_total_bytes::numeric * 100), 2) as compression_pct
    FROM timescaledb_information.compression_chunk_size
)
SELECT decompress_chunk(chunk_name::regclass), compress_chunk(chunk_name::regclass)
FROM compression_stats
WHERE compression_pct < 50  -- Less than 50% compression achieved
AND before_compression_total_bytes > 1000000;  -- Only larger chunks
```

#### 2. Emergency Space Recovery

```sql
-- Step 1: Identify large uncompressed chunks
SELECT
    chunk_name,
    pg_size_pretty(pg_relation_size(chunk_name::regclass)) as size,
    range_start,
    range_end
FROM timescaledb_information.chunks
WHERE hypertable_name = 'market_data'
AND NOT is_compressed
ORDER BY pg_relation_size(chunk_name::regclass) DESC
LIMIT 5;

-- Step 2: Force compress largest chunks
SELECT compress_chunk(i)
FROM (
    SELECT chunk_name as i
    FROM timescaledb_information.chunks
    WHERE hypertable_name = 'market_data'
    AND NOT is_compressed
    ORDER BY pg_relation_size(chunk_name::regclass) DESC
    LIMIT 5
) sub;

-- Step 3: Remove old data if needed
SELECT drop_chunks('market_data',
    older_than => INTERVAL '5 years',
    cascade => true
);
```

#### 3. Optimize Specific Timeframes

```sql
-- Compress hourly data differently from daily data
DO $$
DECLARE
    chunk record;
BEGIN
    FOR chunk IN
        SELECT distinct chunk_name
        FROM timescaledb_information.chunks c
        JOIN market_data m ON m.timestamp BETWEEN c.range_start AND c.range_end
        WHERE c.hypertable_name = 'market_data'
        AND m.timeframe = 'H1'
        AND NOT c.is_compressed
    LOOP
        EXECUTE format('SELECT compress_chunk(%L)', chunk.chunk_name);
    END LOOP;
END $$;
```

## Maintenance Logs

### Location

All maintenance activities are logged to:

```
/var/log/mt5/db_maintenance.log
```

### Log Format

```
[YYYY-MM-DD HH:MM:SS] Starting database maintenance tasks...
[YYYY-MM-DD HH:MM:SS] Running VACUUM ANALYZE...
[YYYY-MM-DD HH:MM:SS] Compressing old chunks...
...
```

## Monitoring and Troubleshooting

### Performance Monitoring

#### 1. Query Performance

```sql
-- Find slow queries (requires pg_stat_statements)
SELECT
    round(total_exec_time::numeric, 2) as total_time,
    calls,
    round(mean_exec_time::numeric, 2) as mean_time,
    round((100 * total_exec_time / sum(total_exec_time) over ())::numeric, 2) as percentage_cpu,
    substring(query, 1, 100) as query_preview
FROM pg_stat_statements
WHERE query ILIKE '%market_data%'
ORDER BY total_exec_time DESC
LIMIT 5;

-- Index usage statistics
SELECT
    schemaname || '.' || tablename as table_name,
    indexrelname as index_name,
    pg_size_pretty(pg_relation_size(quote_ident(schemaname) || '.' || quote_ident(indexrelname)::regclass)) as index_size,
    idx_scan as number_of_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE tablename = 'market_data'
ORDER BY idx_scan DESC;
```

#### 2. Compression Efficiency

```sql
-- Overall compression stats by timeframe
SELECT
    m.timeframe,
    count(distinct c.chunk_name) as total_chunks,
    count(distinct case when c.is_compressed then c.chunk_name end) as compressed_chunks,
    pg_size_pretty(sum(case when c.is_compressed then cs.after_compression_total_bytes else pg_relation_size(c.chunk_name::regclass) end)) as total_size,
    round(avg(case
        when cs.after_compression_total_bytes is not null
        then 100 - (cs.after_compression_total_bytes::numeric / nullif(cs.before_compression_total_bytes, 0) * 100)
        else 0
    end), 2) as avg_compression_ratio
FROM timescaledb_information.chunks c
LEFT JOIN market_data m ON m.timestamp BETWEEN c.range_start AND c.range_end
LEFT JOIN timescaledb_information.compression_chunk_size cs ON c.chunk_name = cs.chunk_name
WHERE c.hypertable_name = 'market_data'
GROUP BY m.timeframe;

-- Compression timeline
SELECT
    date_trunc('day', range_start) as day,
    count(*) as total_chunks,
    count(*) filter (where is_compressed) as compressed_chunks,
    pg_size_pretty(sum(pg_relation_size(chunk_name::regclass))) as total_size
FROM timescaledb_information.chunks
WHERE hypertable_name = 'market_data'
GROUP BY 1
ORDER BY 1 DESC;
```

#### 3. System Health

```sql
-- Check for bloat
SELECT
    schemaname || '.' || tablename as table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)::regclass)) as total_size,
    pg_size_pretty(pg_table_size(quote_ident(schemaname) || '.' || quote_ident(tablename)::regclass)) as table_size,
    pg_size_pretty(pg_indexes_size(quote_ident(schemaname) || '.' || quote_ident(tablename)::regclass)) as index_size,
    round(100 * pg_table_size(quote_ident(schemaname) || '.' || quote_ident(tablename)::regclass) /
          pg_total_relation_size(quote_ident(schemaname) || '.' || quote_ident(tablename)::regclass))::numeric as table_percent
FROM pg_tables
WHERE tablename = 'market_data';

-- Check for dead tuples
SELECT
    schemaname || '.' || relname as table_name,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples,
    round(100 * n_dead_tup::numeric / nullif(n_live_tup, 0), 2) as dead_tuple_percentage,
    last_vacuum,
    last_autovacuum
FROM pg_stat_user_tables
WHERE relname = 'market_data';
```

### Troubleshooting Common Issues

#### 1. Job Management

```sql
-- Check failed jobs
SELECT
    job_id,
    application_name,
    schedule_interval,
    last_run_status,
    last_successful_finish,
    last_run_duration,
    total_failures,
    next_start
FROM timescaledb_information.job_stats
WHERE last_run_status = 'ERROR'
OR total_failures > 0;

-- Job history
SELECT
    job_id,
    application_name,
    substr(sqlerrm, 1, 100) as error_message,
    finish_time,
    next_start
FROM _timescaledb_internal.bgw_job_stat
ORDER BY finish_time DESC
LIMIT 5;
```

#### 2. Lock Monitoring

```sql
-- Check for blocking/blocked queries
SELECT
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.GRANTED;
```

#### 3. Space Usage Analysis

```sql
-- Detailed space analysis
WITH RECURSIVE
chunks AS (
    SELECT
        chunk_name,
        range_start,
        range_end,
        is_compressed,
        pg_relation_size(chunk_name::regclass) as chunk_size
    FROM timescaledb_information.chunks
    WHERE hypertable_name = 'market_data'
),
chunk_stats AS (
    SELECT
        date_trunc('month', range_start) as month,
        sum(chunk_size) as total_size,
        count(*) as chunk_count,
        sum(case when is_compressed then 1 else 0 end) as compressed_chunks
    FROM chunks
    GROUP BY 1
)
SELECT
    month,
    pg_size_pretty(total_size) as size,
    chunk_count,
    compressed_chunks,
    round(100 * compressed_chunks::numeric / chunk_count, 2) as compression_percent
FROM chunk_stats
ORDER BY month DESC;

### Manual Policy Control

Start/Stop Policies:
```sql
-- Pause a policy
SELECT alter_job(1004, scheduled => false);  -- 1004 is the job_id

-- Resume a policy
SELECT alter_job(1004, scheduled => true);
```

## Backup and Recovery Procedures

### Backup Types

#### 1. Full Database Backup

```bash
# Logical backup (pg_dump)
docker exec mt5_db pg_dump \
    -U trader \
    -d mt5_trading \
    -F c \
    -Z 9 \
    -f /backups/mt5_trading_$(date +%Y%m%d).backup

# Physical backup (pg_basebackup)
docker exec mt5_db pg_basebackup \
    -U trader \
    -D /backups/base_$(date +%Y%m%d) \
    -Ft -z -P
```

#### 2. Selective Backup

```bash
# Backup specific tables
docker exec mt5_db pg_dump \
    -U trader \
    -d mt5_trading \
    -t market_data \
    -t ml_predictions \
    -F c \
    -Z 9 \
    -f /backups/market_data_$(date +%Y%m%d).backup

# Backup specific time range
docker exec mt5_db pg_dump \
    -U trader \
    -d mt5_trading \
    --table='(SELECT * FROM market_data WHERE timestamp > NOW() - INTERVAL '\''30 days'\'')' \
    -F c \
    -f /backups/recent_data_$(date +%Y%m%d).backup
```

#### 3. Models Backup

```bash
# Backup ML models
docker run --rm \
    -v models_mt5:/models \
    -v /backups:/backup \
    busybox tar czf \
    /backup/models_$(date +%Y%m%d).tar.gz \
    -C /models .
```

### Automated Backup Script

```bash
#!/bin/bash
# /usr/local/bin/mt5_backup.sh
set -euo pipefail

# Configuration
BACKUP_DIR="/backups/mt5"
RETAIN_DAYS=14
DATE=$(date +%Y%m%d)
LOG_FILE="/var/log/mt5/backup.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"/{db,models,configs}

# 1. Database backup
log "Starting database backup..."
docker exec mt5_db pg_dump \
    -U trader \
    -d mt5_trading \
    -F c \
    -Z 9 \
    -f /backups/mt5_trading_$DATE.backup

# 2. Models backup
log "Starting models backup..."
docker run --rm \
    -v models_mt5:/models \
    -v "$BACKUP_DIR/models":/backup \
    busybox tar czf \
    /backup/models_$DATE.tar.gz \
    -C /models .

# 3. Configuration backup
log "Backing up configurations..."
tar czf "$BACKUP_DIR/configs/config_$DATE.tar.gz" \
    -C /home/felipe/mt5-trading-db \
    docker-compose.yml \
    .env \
    api/config.py

# Cleanup old backups
log "Cleaning up old backups..."
find "$BACKUP_DIR" -type f -mtime +$RETAIN_DAYS -delete

log "Backup completed successfully"
```

### Recovery Procedures

#### 1. Full Database Restore

```bash
# Stop services
docker-compose stop

# Restore database
docker exec -i mt5_db pg_restore \
    -U trader \
    -d mt5_trading \
    -c \
    -F c \
    /backups/mt5_trading_20251016.backup

# Restore models
docker run --rm \
    -v models_mt5:/models \
    -v /backups:/backup \
    busybox sh -c \
    'cd /models && tar xzf /backup/models_20251016.tar.gz'

# Restart services
docker-compose up -d
```

#### 2. Point-in-Time Recovery

```bash
# Stop the database
docker-compose stop db

# Restore to specific timestamp
docker exec -i mt5_db psql -U trader -d mt5_trading << EOF
SELECT timescaledb_experimental.restore_point('before_incident');
RESTORE POINT 'before_incident';
EOF

# Restart services
docker-compose up -d
```

#### 3. Selective Data Recovery

```sql
-- Create temporary table for recovery
CREATE TABLE market_data_recovery (LIKE market_data);

-- Restore specific data
\! docker exec -i mt5_db pg_restore \
    -U trader \
    -d mt5_trading \
    -t market_data_recovery \
    /backups/market_data_20251016.backup

-- Recover specific records
INSERT INTO market_data
SELECT * FROM market_data_recovery
WHERE symbol = 'EURUSD'
AND timestamp BETWEEN '2025-10-01' AND '2025-10-15';

-- Cleanup
DROP TABLE market_data_recovery;
```

### Backup Monitoring and Alerting

#### 1. Automated Monitoring System

The backup monitoring system (`scripts/monitor_backups.sh`) checks:

- Backup freshness (age of latest backups)
- Backup integrity
- Backup sizes
- Disk space usage
- Error patterns in logs

#### 2. Monitoring Schedule

```bash
# Hourly monitoring check
0 * * * * /home/felipe/mt5-trading-db/scripts/monitor_backups.sh

# Post-backup verification
45 2 * * * /home/felipe/mt5-trading-db/scripts/monitor_backups.sh
```

#### 3. Alert Channels

- Email notifications
- Discord alerts (optional)
- Slack notifications (optional)
- System logs (`/var/log/mt5/backup_monitor.log`)

#### 4. Monitoring Thresholds

```bash
# Default thresholds (configurable in monitor_backups.sh)
MAX_BACKUP_AGE=25         # Hours
MIN_BACKUP_SIZE=1000000   # 1MB in bytes
MAX_FAILED_BACKUPS=2      # Consecutive failures
DISK_USAGE_THRESHOLD=85   # Percentage
```

#### 5. Manual Verification Tools

##### Database Backup Verification

```bash
# Quick integrity check
docker exec mt5_db pg_restore -l /backups/mt5_trading_20251016.backup

# Detailed verification (test restore)
docker exec mt5_db createdb mt5_trading_test
docker exec mt5_db pg_restore \
    -U trader \
    -d mt5_trading_test \
    /backups/mt5_trading_20251016.backup

# Compare record counts
docker exec -i mt5_db psql -U trader << EOF
SELECT
    'Production' as db,
    count(*) as records,
    min(timestamp) as oldest,
    max(timestamp) as newest
FROM mt5_trading.market_data
UNION ALL
SELECT
    'Backup' as db,
    count(*) as records,
    min(timestamp) as oldest,
    max(timestamp) as newest
FROM mt5_trading_test.market_data;
EOF
```

##### Models Backup Verification

```bash
# Check model files integrity
tar tvf /backups/mt5/models/models_20251016.tar.gz

# Verify model checksums
sha256sum /backups/mt5/models/models_*.tar.gz > checksums.txt
```

##### Space Usage Monitoring

```sql
-- Monitor backup growth
SELECT
    date_trunc('day', backup_time) as backup_date,
    count(*) as backup_count,
    pg_size_pretty(sum(backup_size)) as total_size,
    round(avg(compression_ratio), 2) as avg_compression
FROM (
    SELECT
        to_timestamp(substring(filename from '\d{8}')::int::text, 'YYYYMMDD') as backup_time,
        size as backup_size,
        (original_size::float / size) as compression_ratio
    FROM (
        SELECT
            filename,
            stat.size,
            substring(filename from '_(\d+)\.backup$') as backup_date,
            -- Get original size from backup header
            (pg_restore -l filename | grep 'DATA' | awk '{sum += $3} END {print sum}') as original_size
        FROM pg_ls_dir('/backups/mt5/db') as backup(filename)
        JOIN pg_stat_file('/backups/mt5/db/' || filename) as stat ON true
        WHERE filename ~ '\.backup$'
    ) as f
) as backup_stats
GROUP BY 1
ORDER BY 1 DESC
LIMIT 7;
```

#### 6. Alert Examples

##### Critical Alerts

- Backup age exceeds 25 hours
- Backup size below 1MB
- Multiple consecutive backup failures
- Disk usage above 85%
- Integrity check failures

##### Warning Alerts

- Unexpected backup size changes (>50% difference)
- New backup smaller than previous
- Compression ratio anomalies
- Slow backup completion time

#### 7. Monitoring Dashboard Queries

```sql
-- Backup success rate (last 7 days)
WITH backup_status AS (
    SELECT
        date_trunc('day', timestamp) as backup_date,
        count(*) as total_attempts,
        count(*) filter (where status = 'SUCCESS') as successful
    FROM (
        SELECT
            timestamp,
            CASE WHEN message ~ 'ERROR|FAILED' THEN 'FAILED' ELSE 'SUCCESS' END as status
        FROM pg_read_file_lines('/var/log/mt5/backup.log') as lines
        WHERE lines ~ '^\[\d{4}-\d{2}-\d{2}'
    ) as log_entries
    GROUP BY 1
)
SELECT
    backup_date,
    total_attempts,
    successful,
    round(100.0 * successful / total_attempts, 2) as success_rate
FROM backup_status
ORDER BY backup_date DESC
LIMIT 7;

-- Backup timing trends
SELECT
    date_trunc('day', start_time) as backup_date,
    avg(extract(epoch from (end_time - start_time))) as avg_duration_seconds,
    max(extract(epoch from (end_time - start_time))) as max_duration_seconds
FROM (
    SELECT
        timestamp as start_time,
        lead(timestamp) over (order by timestamp) as end_time
    FROM pg_read_file_lines('/var/log/mt5/backup.log') as lines
    WHERE lines ~ 'Starting|completed'
) as backup_times
GROUP BY 1
ORDER BY 1 DESC
LIMIT 7;
```

### Recovery After System Crash

#### 1. Check System Status

```sql
-- Check policy status
SELECT * FROM timescaledb_information.job_stats;

-- Verify chunk health
SELECT * FROM chunks_detailed_size('market_data');
```

#### 2. Run Recovery Steps

```bash
# Check and repair any inconsistencies
docker exec -i mt5_db psql -U trader -d mt5_trading << EOF
SELECT chunk_name,
       range_start,
       range_end
FROM timescaledb_information.chunks
WHERE hypertable_name = 'market_data'
ORDER BY range_start DESC;

-- Recompress any uncompressed chunks
SELECT compress_chunk(i)
FROM show_chunks('market_data', older_than => INTERVAL '30 days') i
WHERE i NOT IN (
    SELECT chunk_name
    FROM timescaledb_information.chunks
    WHERE is_compressed = true
);
EOF

# Run maintenance script
/home/felipe/mt5-trading-db/scripts/db_maintenance.sh
```

### Performance Issues

If query performance degrades:

1. Run manual VACUUM ANALYZE
2. Check compression status
3. Verify chunk time ranges are appropriate
4. Review and adjust retention policies if needed

## Changes applied by automation

I applied the following repository changes to improve reliability, security and operations:

- `docker-compose.yml` and `docker-compose.override.yml`: added restart, healthchecks, logging limits, deploy resource limits and marked `models_mt5` external.
- `scripts/health_unhealthy_check.sh`: helper script to detect unhealthy containers.
- `scripts/install_cron_restart.sh`: installs an `@reboot` crontab entry to run `docker-compose up -d` on boot.
- `scripts/freeze_requirements.sh`: helper to generate `requirements.lock` files (run inside venvs).
- `docker/logrotate/mt5-containers`: logrotate config to rotate Docker container logs and `/var/log/mt5` logs.

Next steps (run on the host, some require sudo):

1. Ensure external volume exists: `docker volume create --name models_mt5`
2. Copy logrotate file to system: `sudo cp docker/logrotate/mt5-containers /etc/logrotate.d/mt5-containers`
3. Install reboot cron (runs as current user): `scripts/install_cron_restart.sh`
4. (Optional) Run `scripts/freeze_requirements.sh` inside each service virtualenv to capture pip frozen versions.
5. Review `docker-compose.yml` postgres -c flags and move persistent settings to a postgresql.conf when you tune for production RAM.

If you want, I can apply the host-level steps that require sudo (install logrotate, create cron for you, create the external volume). Tell me which ones to run and I'll execute them.
