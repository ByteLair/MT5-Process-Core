# Connection Pooling Documentation

Complete guide for database connection pooling in the MT5 Trading system.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [PgBouncer Configuration](#pgbouncer-configuration)
- [SQLAlchemy Configuration](#sqlalchemy-configuration)
- [PostgreSQL Tuning](#postgresql-tuning)
- [Monitoring](#monitoring)
- [Load Testing](#load-testing)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

The MT5 Trading system uses a two-tier connection pooling strategy:

1. **PgBouncer** - Connection pooler between application and PostgreSQL
2. **SQLAlchemy QueuePool** - Application-level connection pool

This architecture provides:

- **Reduced Connection Overhead**: Reuse database connections instead of creating new ones
- **Resource Efficiency**: Limit total connections to PostgreSQL
- **Scalability**: Support many concurrent clients with fewer database connections
- **Performance**: Lower latency for query execution
- **Stability**: Protection against connection exhaustion

### Connection Flow

```
API Clients (1000+)
    ↓
SQLAlchemy Pool (5 + 10 overflow)
    ↓
PgBouncer (25 default pool + 5 reserve)
    ↓
PostgreSQL (200 max connections)
```

## Architecture

### PgBouncer Transaction Pooling

**Pool Mode**: `transaction`

In transaction pooling mode:

- Connections are assigned to clients for the duration of a transaction
- After `COMMIT`/`ROLLBACK`, connection returns to pool
- Most efficient for OLTP workloads
- Compatible with most applications

**Key Settings**:

- `max_client_conn: 1000` - Maximum concurrent clients
- `default_pool_size: 25` - Core pool size per user/database
- `min_pool_size: 10` - Always maintain minimum connections
- `reserve_pool_size: 5` - Additional connections for peak loads
- `max_db_connections: 50` - Total server connections per database

### SQLAlchemy QueuePool

**Pool Type**: `QueuePool` (default)

QueuePool maintains a fixed pool of connections:

- Creates connections up to `pool_size`
- Can overflow up to `max_overflow` additional connections
- Overflow connections are discarded after use
- Thread-safe connection checkout/checkin

**With PgBouncer** (recommended):

```python
pool_size = 5          # Small, PgBouncer handles pooling
max_overflow = 10      # Limited overflow
pool_timeout = 10      # Quick failure detection
pool_recycle = 1800    # 30 minutes
```

**Without PgBouncer** (direct PostgreSQL):

```python
pool_size = 20         # Larger pool
max_overflow = 30      # More overflow capacity
pool_timeout = 30      # Longer timeout
pool_recycle = 3600    # 1 hour
```

## PgBouncer Configuration

### Installation

PgBouncer is deployed as a Docker container:

```yaml
# docker-compose.yml
pgbouncer:
  image: edoburu/pgbouncer:1.21.0
  container_name: mt5_pgbouncer
  ports:
    - "6432:5432"
  environment:
    DATABASE_URL: "postgres://trader:password@db:5432/mt5_trading"
    POOL_MODE: transaction
    MAX_CLIENT_CONN: 1000
    DEFAULT_POOL_SIZE: 25
```

### Configuration File

See `pgbouncer/pgbouncer.ini` for complete configuration.

Key sections:

#### Databases

```ini
[databases]
mt5_trading = host=db port=5432 dbname=mt5_trading
```

#### Authentication

```ini
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
```

Generate userlist with MD5 hashes:

```bash
./scripts/generate_userlist.sh
```

#### Pool Sizes

```ini
# Maximum concurrent clients
max_client_conn = 1000

# Core pool size
default_pool_size = 25

# Minimum maintained connections
min_pool_size = 10

# Peak load capacity
reserve_pool_size = 5

# Total database connections
max_db_connections = 50
```

#### Timeouts

```ini
# Close idle server connections after 10 minutes
server_idle_timeout = 600

# Recycle server connections after 1 hour
server_lifetime = 3600

# Connection establishment timeout
server_connect_timeout = 15

# Client idle timeout (0 = disabled)
client_idle_timeout = 0

# Query timeout (0 = let PostgreSQL handle)
query_timeout = 0
```

#### Performance Tuning

```ini
# TCP settings for better connection handling
so_reuseport = 1
tcp_keepalive = 1
tcp_keepidle = 60
tcp_keepintvl = 10
tcp_keepcnt = 5
tcp_user_timeout = 30000

# Ignore parameters that cause connection churn
ignore_startup_parameters = extra_float_digits,application_name

# Disable prepared statements (transaction pooling)
max_prepared_statements = 0
```

### Starting PgBouncer

```bash
# Start PgBouncer service
docker-compose up -d pgbouncer

# Check logs
docker-compose logs -f pgbouncer

# Verify connectivity
psql -h localhost -p 6432 -U trader -d mt5_trading
```

### PgBouncer Admin Console

Connect to admin console:

```bash
psql -h localhost -p 6432 -U trader -d pgbouncer
```

Useful commands:

```sql
-- Show pool statistics
SHOW POOLS;

-- Show database statistics
SHOW DATABASES;

-- Show client connections
SHOW CLIENTS;

-- Show server connections
SHOW SERVERS;

-- Show configuration
SHOW CONFIG;

-- Show statistics
SHOW STATS;

-- Reload configuration
RELOAD;

-- Pause all connections
PAUSE;

-- Resume connections
RESUME;

-- Graceful shutdown
SHUTDOWN;
```

## SQLAlchemy Configuration

### Connection String

The system automatically uses PgBouncer by default:

```python
from api.config import get_db_url

# Uses PgBouncer by default (port 6432)
db_url = get_db_url()
# postgresql+psycopg://trader:trader123@pgbouncer:5432/mt5_trading

# To bypass PgBouncer, set environment variable
# USE_PGBOUNCER=false
```

### Pool Configuration

```python
from api.config import get_sqlalchemy_pool_config, get_db_connect_args
from sqlalchemy import create_engine

engine = create_engine(
    get_db_url(),
    **get_sqlalchemy_pool_config(),
    connect_args=get_db_connect_args()
)
```

### Environment Variables

Configure connection pooling via `.env`:

```bash
# Enable/disable PgBouncer
USE_PGBOUNCER=true

# SQLAlchemy pool settings (with PgBouncer)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=10
DB_POOL_RECYCLE=1800
DB_POOL_PRE_PING=true

# Connection settings
DB_PREPARE_THRESHOLD=0      # Disable prepared statements for transaction pooling
DB_CONNECT_TIMEOUT=10
```

### Connection Usage

Always use context managers:

```python
from sqlalchemy import create_engine, text

engine = create_engine(get_db_url(), **get_sqlalchemy_pool_config())

# Correct usage - connection automatically returned to pool
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM candles LIMIT 10"))
    rows = result.fetchall()

# Connection is now back in the pool
```

Avoid:

```python
# DON'T: Connection never returned to pool
conn = engine.connect()
result = conn.execute(text("SELECT ..."))
# Missing conn.close() - connection leak!
```

## PostgreSQL Tuning

### Connection Limits

Configured in `docker/postgres.conf.d/postgresql.conf`:

```ini
# Increased for PgBouncer connection pooling
max_connections = 200

# Reserved for admin/maintenance
superuser_reserved_connections = 5

# Kill idle transactions after 10 minutes
idle_in_transaction_session_timeout = 600000
```

### TCP Keepalive

```ini
tcp_keepalives_idle = 60
tcp_keepalives_interval = 10
tcp_keepalives_count = 5
```

### Memory Settings

```ini
# 25% of RAM
shared_buffers = '7GB'

# Per-operation memory
work_mem = '32MB'

# Maintenance operations
maintenance_work_mem = '512MB'

# 50-75% of RAM
effective_cache_size = '15GB'
```

### Connection Monitoring

```sql
-- Current connections
SELECT
    count(*) as total,
    state,
    application_name
FROM pg_stat_activity
WHERE datname = 'mt5_trading'
GROUP BY state, application_name;

-- Connection usage over time
SELECT
    now() - backend_start as connection_age,
    usename,
    application_name,
    state,
    query
FROM pg_stat_activity
WHERE datname = 'mt5_trading'
ORDER BY backend_start;

-- Max connections reached?
SELECT
    count(*) as current_connections,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections,
    round(count(*)::numeric / (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') * 100, 2) as usage_percent
FROM pg_stat_activity;
```

## Monitoring

### Prometheus Metrics

The system exports comprehensive connection pool metrics:

#### SQLAlchemy Metrics

**Gauges** (current state):

- `sqlalchemy_pool_size` - Current pool size
- `sqlalchemy_pool_checked_in` - Available connections
- `sqlalchemy_pool_checked_out` - Active connections
- `sqlalchemy_pool_overflow` - Overflow connections
- `sqlalchemy_pool_waiters` - Threads waiting for connection

**Counters** (cumulative):

- `sqlalchemy_pool_connects_total` - New connections created
- `sqlalchemy_pool_disconnects_total` - Connections closed
- `sqlalchemy_pool_checkouts_total` - Connection checkouts
- `sqlalchemy_pool_checkins_total` - Connection checkins
- `sqlalchemy_pool_invalidations_total` - Connection invalidations

**Histograms**:

- `sqlalchemy_pool_checkout_duration_seconds` - Time waiting for connection

#### PgBouncer Metrics

**Databases**:

- `pgbouncer_databases_current_connections` - Active database connections
- `pgbouncer_databases_pool_size` - Server connections in pool

**Pools**:

- `pgbouncer_pools_cl_active` - Active client connections
- `pgbouncer_pools_cl_waiting` - Clients waiting for connection
- `pgbouncer_pools_sv_active` - Active server connections
- `pgbouncer_pools_sv_idle` - Idle server connections
- `pgbouncer_pools_maxwait` - Age of oldest waiting client

### Setup Monitoring

```python
from api.pool_monitoring import (
    setup_sqlalchemy_pool_metrics,
    update_sqlalchemy_pool_metrics,
    collect_pgbouncer_metrics
)

# Setup event listeners
setup_sqlalchemy_pool_metrics(engine, pool_name="default")

# Periodic updates (in background task)
import asyncio

async def update_metrics():
    while True:
        update_sqlalchemy_pool_metrics(engine, pool_name="default")
        collect_pgbouncer_metrics(
            pgbouncer_host="pgbouncer",
            pgbouncer_user="trader",
            pgbouncer_password=os.getenv("POSTGRES_PASSWORD")
        )
        await asyncio.sleep(15)
```

### Grafana Dashboard

Access the Connection Pool dashboard:

**URL**: <http://192.168.15.20:3000/d/connection-pool-monitoring>

Dashboard includes:

- Pool utilization gauge
- Connection status (checked out, waiting, size)
- Connection operations rate
- Checkout duration percentiles
- PgBouncer pool statistics
- Invalidations and errors

Key panels:

1. **SQLAlchemy Pool Utilization** - Should stay below 75%
2. **Connections Waiting** - Should be 0 (or very low)
3. **Connection Checkout Duration** - P99 should be < 100ms
4. **PgBouncer Max Wait Time** - Should be < 5 seconds
5. **Pool Invalidations** - Should be minimal

### PromQL Queries

**Pool Utilization**:

```promql
(sqlalchemy_pool_checked_out{pool_name="default"} /
 (sqlalchemy_pool_size{pool_name="default"} +
  sqlalchemy_pool_overflow{pool_name="default"})) * 100
```

**Checkout Rate**:

```promql
rate(sqlalchemy_pool_checkouts_total{pool_name="default"}[5m])
```

**P95 Checkout Duration**:

```promql
histogram_quantile(0.95,
  rate(sqlalchemy_pool_checkout_duration_seconds_bucket{pool_name="default"}[5m]))
```

**PgBouncer Clients Waiting**:

```promql
pgbouncer_pools_cl_waiting{database="mt5_trading"}
```

### Health Checks

```python
from api.pool_monitoring import check_pool_health

# Check pool health
health = check_pool_health(engine, pool_name="default")

print(health)
# {
#     "pool_name": "default",
#     "status": "healthy",  # or "warning", "critical", "error"
#     "size": 5,
#     "checked_out": 2,
#     "checked_in": 3,
#     "overflow": 0,
#     "utilization_percent": 13.33,
#     "total_capacity": 15
# }
```

## Load Testing

### Load Test Script

Run comprehensive load tests:

```bash
./scripts/load_test_pool.py --help
```

### Test Scenarios

#### 1. Concurrent Load Test

Test sustained concurrent load:

```bash
# 1000 queries with 50 concurrent workers
./scripts/load_test_pool.py \
    --test-type concurrent \
    --num-queries 1000 \
    --num-workers 50 \
    --query-type simple

# More intensive test
./scripts/load_test_pool.py \
    --test-type concurrent \
    --num-queries 5000 \
    --num-workers 200 \
    --query-type complex
```

#### 2. Burst Load Test

Test periodic traffic spikes:

```bash
# 10 bursts of 100 queries
./scripts/load_test_pool.py \
    --test-type burst \
    --burst-size 100 \
    --num-bursts 10 \
    --burst-interval 2.0

# Heavy bursts
./scripts/load_test_pool.py \
    --test-type burst \
    --burst-size 500 \
    --num-bursts 5 \
    --burst-interval 1.0
```

#### 3. Pool Configuration Testing

Test different pool configurations:

```bash
# Small pool
./scripts/load_test_pool.py \
    --pool-size 3 \
    --max-overflow 5 \
    --num-queries 1000 \
    --num-workers 50

# Large pool
./scripts/load_test_pool.py \
    --pool-size 20 \
    --max-overflow 30 \
    --num-queries 1000 \
    --num-workers 50
```

### Interpreting Results

Good performance indicators:

- **Success Rate**: > 99%
- **Mean Duration**: < 50ms for simple queries
- **P95 Duration**: < 100ms
- **P99 Duration**: < 500ms
- **Failures**: < 1%

Warning signs:

- Success rate < 95%
- P99 duration > 1 second
- Many connection timeouts
- Increasing checkout duration over time

## Troubleshooting

### Common Issues

#### 1. Connection Timeout

**Symptom**: `QueuePool limit exceeded` or `Connection timeout`

**Causes**:

- Pool too small for load
- Long-running queries holding connections
- Connection leaks (not returning to pool)

**Solutions**:

```bash
# Increase pool size
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Check for connection leaks
SELECT count(*), state FROM pg_stat_activity
WHERE datname = 'mt5_trading'
GROUP BY state;

# Look for long-running queries
SELECT
    pid,
    now() - query_start as duration,
    state,
    query
FROM pg_stat_activity
WHERE datname = 'mt5_trading'
  AND state != 'idle'
ORDER BY duration DESC;
```

#### 2. PgBouncer Max Wait Time High

**Symptom**: `pgbouncer_pools_maxwait` > 30 seconds

**Causes**:

- PgBouncer pool too small
- PostgreSQL slow or overloaded
- Long transactions

**Solutions**:

```ini
# Increase PgBouncer pool sizes
DEFAULT_POOL_SIZE=50
RESERVE_POOL_SIZE=10
MAX_DB_CONNECTIONS=100

# Check PgBouncer stats
psql -h localhost -p 6432 -U trader -d pgbouncer
SHOW POOLS;
SHOW SERVERS;
```

#### 3. Connection Invalidations

**Symptom**: High `sqlalchemy_pool_invalidations_total`

**Causes**:

- Database restarts
- Network issues
- Idle connection timeouts

**Solutions**:

```python
# Enable pre-ping to detect stale connections
DB_POOL_PRE_PING=true

# Reduce pool_recycle time
DB_POOL_RECYCLE=900  # 15 minutes
```

#### 4. PgBouncer Not Working

**Symptom**: Applications can't connect via PgBouncer

**Checks**:

```bash
# Check PgBouncer is running
docker-compose ps pgbouncer

# Check logs
docker-compose logs pgbouncer

# Verify userlist.txt
cat pgbouncer/userlist.txt

# Test connection
psql -h localhost -p 6432 -U trader -d mt5_trading

# Check PgBouncer configuration
docker exec -it mt5_pgbouncer cat /etc/pgbouncer/pgbouncer.ini
```

**Common fixes**:

```bash
# Regenerate userlist.txt
./scripts/generate_userlist.sh

# Restart PgBouncer
docker-compose restart pgbouncer

# Check authentication
docker-compose logs pgbouncer | grep -i auth
```

### Debug Mode

Enable detailed logging:

```bash
# SQLAlchemy pool logging
DB_ECHO_POOL=true

# PgBouncer verbose logging
# Edit pgbouncer/pgbouncer.ini
verbose = 3
log_connections = 1
log_disconnections = 1
log_pooler_errors = 1
```

## Best Practices

### Application Code

1. **Always use context managers**:

   ```python
   with engine.connect() as conn:
       result = conn.execute(query)
   ```

2. **Keep connections short-lived**:

   ```python
   # Good: Quick query
   with engine.connect() as conn:
       result = conn.execute(text("SELECT ..."))
       return result.fetchall()

   # Bad: Holding connection during processing
   with engine.connect() as conn:
       result = conn.execute(text("SELECT ..."))
       data = result.fetchall()
       # Long processing here while holding connection
       processed = expensive_computation(data)
   ```

3. **Use connection pooling, not connection per request**:

   ```python
   # Good: Shared engine with pool
   engine = create_engine(...)  # Once at startup

   @app.get("/data")
   def get_data():
       with engine.connect() as conn:
           return conn.execute(...)

   # Bad: New engine per request
   @app.get("/data")
   def get_data():
       engine = create_engine(...)  # DON'T DO THIS
       return engine.execute(...)
   ```

4. **Handle exceptions properly**:

   ```python
   try:
       with engine.connect() as conn:
           result = conn.execute(query)
   except OperationalError:
       # Connection error - will be invalidated automatically
       logger.error("Database connection error")
       raise
   ```

### Configuration

1. **Start conservative, scale up**:
   - Begin with small pool sizes
   - Monitor metrics
   - Increase only if needed

2. **PgBouncer pool sizes**:
   - `default_pool_size` = 25-50 (typical)
   - `max_db_connections` = 2x default_pool_size
   - Always < PostgreSQL `max_connections`

3. **SQLAlchemy pool sizes** (with PgBouncer):
   - `pool_size` = 5-10 (small)
   - `max_overflow` = 10-20
   - `pool_timeout` = 10-30 seconds

4. **Timeouts**:
   - Connection timeout: 10-15s
   - Pool timeout: 10-30s
   - Query timeout: Let PostgreSQL handle

### Monitoring

1. **Set up alerts**:
   - Pool utilization > 75%
   - Connections waiting > 0
   - P99 checkout duration > 500ms
   - PgBouncer maxwait > 30s

2. **Regular health checks**:

   ```python
   # Every 5 minutes
   health = check_pool_health(engine)
   if health["status"] != "healthy":
       send_alert(health)
   ```

3. **Review metrics weekly**:
   - Connection patterns
   - Peak utilization times
   - Query duration trends
   - Error rates

### Deployment

1. **Configuration changes**:

   ```bash
   # Update environment variables
   vim .env

   # Restart services
   docker-compose restart pgbouncer api

   # Verify
   docker-compose logs -f pgbouncer
   ```

2. **PgBouncer reload** (zero downtime):

   ```bash
   # Reload configuration without dropping connections
   psql -h localhost -p 6432 -U trader -d pgbouncer -c "RELOAD;"
   ```

3. **PostgreSQL changes**:

   ```bash
   # Edit configuration
   vim docker/postgres.conf.d/postgresql.conf

   # Reload (no restart needed for most settings)
   docker exec mt5_db pg_ctl reload

   # Or restart if needed
   docker-compose restart db
   ```

### Performance Tuning Checklist

- [ ] PgBouncer running and healthy
- [ ] Userlist.txt generated with correct password hashes
- [ ] SQLAlchemy configured to use PgBouncer
- [ ] Pool sizes appropriate for workload
- [ ] Pre-ping enabled
- [ ] Prepared statements disabled (transaction pooling)
- [ ] Timeouts configured
- [ ] Monitoring and metrics working
- [ ] Grafana dashboard accessible
- [ ] Load tests passing
- [ ] Connection leaks checked
- [ ] Alerts configured

---

## Quick Reference

### Ports

- PostgreSQL: 5432 (internal)
- PgBouncer: 6432 (external)
- Prometheus: 9090
- Grafana: 3000

### Key Files

- `docker-compose.yml` - Service configuration
- `pgbouncer/pgbouncer.ini` - PgBouncer configuration
- `pgbouncer/userlist.txt` - Authentication
- `api/config.py` - SQLAlchemy configuration
- `api/pool_monitoring.py` - Metrics collection
- `.env` - Environment variables

### Useful Commands

```bash
# Generate userlist
./scripts/generate_userlist.sh

# Run load test
./scripts/load_test_pool.py --test-type concurrent --num-queries 1000

# Check PgBouncer stats
psql -h localhost -p 6432 -U trader -d pgbouncer -c "SHOW POOLS;"

# View pool metrics
curl -s http://localhost:9090/api/v1/query?query=sqlalchemy_pool_size

# Check pool health in Python
python -c "from api.pool_monitoring import check_pool_health; from api.config import get_db_url, get_sqlalchemy_pool_config; from sqlalchemy import create_engine; engine = create_engine(get_db_url(), **get_sqlalchemy_pool_config()); print(check_pool_health(engine))"
```

---

For more information, see:

- [PgBouncer Documentation](https://www.pgbouncer.org/usage.html)
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [PostgreSQL Connection Management](https://www.postgresql.org/docs/current/runtime-config-connection.html)
