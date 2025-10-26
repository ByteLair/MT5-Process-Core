"""
Connection Pool Monitoring for MT5 Trading API

Provides Prometheus metrics for SQLAlchemy and PgBouncer connection pools.
"""

import logging
import time
from contextlib import contextmanager
from typing import Any

import psycopg
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

# ==================== SQLAlchemy Pool Metrics ====================

# Gauge metrics for current pool state
sqlalchemy_pool_size = Gauge(
    "sqlalchemy_pool_size",
    "Current size of the SQLAlchemy connection pool",
    ["pool_name"],
)

sqlalchemy_pool_checked_in = Gauge(
    "sqlalchemy_pool_checked_in",
    "Number of connections currently checked into the pool",
    ["pool_name"],
)

sqlalchemy_pool_checked_out = Gauge(
    "sqlalchemy_pool_checked_out",
    "Number of connections currently checked out from the pool",
    ["pool_name"],
)

sqlalchemy_pool_overflow = Gauge(
    "sqlalchemy_pool_overflow",
    "Number of overflow connections (beyond pool_size)",
    ["pool_name"],
)

sqlalchemy_pool_waiters = Gauge(
    "sqlalchemy_pool_waiters",
    "Number of threads waiting for a connection",
    ["pool_name"],
)

# Counter metrics for pool events
sqlalchemy_pool_connects = Counter(
    "sqlalchemy_pool_connects_total",
    "Total number of connections created",
    ["pool_name"],
)

sqlalchemy_pool_disconnects = Counter(
    "sqlalchemy_pool_disconnects_total",
    "Total number of connections closed",
    ["pool_name"],
)

sqlalchemy_pool_checkouts = Counter(
    "sqlalchemy_pool_checkouts_total",
    "Total number of connection checkouts",
    ["pool_name"],
)

sqlalchemy_pool_checkins = Counter(
    "sqlalchemy_pool_checkins_total",
    "Total number of connection checkins",
    ["pool_name"],
)

sqlalchemy_pool_invalidations = Counter(
    "sqlalchemy_pool_invalidations_total",
    "Total number of connection invalidations",
    ["pool_name"],
)

# Histogram for checkout duration
sqlalchemy_pool_checkout_duration = Histogram(
    "sqlalchemy_pool_checkout_duration_seconds",
    "Time spent waiting for a connection",
    ["pool_name"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ==================== PgBouncer Metrics ====================

pgbouncer_databases_current_connections = Gauge(
    "pgbouncer_databases_current_connections",
    "Current number of connections to database",
    ["database"],
)

pgbouncer_databases_pool_size = Gauge(
    "pgbouncer_databases_pool_size", "Server connections in pool", ["database"]
)

pgbouncer_pools_cl_active = Gauge(
    "pgbouncer_pools_cl_active", "Active client connections", ["database", "user"]
)

pgbouncer_pools_cl_waiting = Gauge(
    "pgbouncer_pools_cl_waiting",
    "Client connections waiting for a server connection",
    ["database", "user"],
)

pgbouncer_pools_sv_active = Gauge(
    "pgbouncer_pools_sv_active", "Active server connections", ["database", "user"]
)

pgbouncer_pools_sv_idle = Gauge(
    "pgbouncer_pools_sv_idle", "Idle server connections", ["database", "user"]
)

pgbouncer_pools_sv_used = Gauge(
    "pgbouncer_pools_sv_used",
    "Server connections that have been used",
    ["database", "user"],
)

pgbouncer_pools_sv_tested = Gauge(
    "pgbouncer_pools_sv_tested",
    "Server connections currently being tested",
    ["database", "user"],
)

pgbouncer_pools_sv_login = Gauge(
    "pgbouncer_pools_sv_login",
    "Server connections currently logging in",
    ["database", "user"],
)

pgbouncer_pools_maxwait = Gauge(
    "pgbouncer_pools_maxwait",
    "Age of oldest unserved client connection",
    ["database", "user"],
)

# ==================== SQLAlchemy Pool Event Listeners ====================


def setup_sqlalchemy_pool_metrics(engine: Engine, pool_name: str = "default"):
    """
    Setup Prometheus metrics collection for SQLAlchemy connection pool.

    Args:
        engine: SQLAlchemy Engine instance
        pool_name: Name for the pool in metrics labels
    """
    pool = engine.pool

    @event.listens_for(pool, "connect")
    def on_connect(dbapi_conn, connection_record):
        """Track new connections."""
        sqlalchemy_pool_connects.labels(pool_name=pool_name).inc()
        logger.debug(f"Pool '{pool_name}': New connection created")

    @event.listens_for(pool, "close")
    def on_close(dbapi_conn, connection_record):
        """Track connection closures."""
        sqlalchemy_pool_disconnects.labels(pool_name=pool_name).inc()
        logger.debug(f"Pool '{pool_name}': Connection closed")

    @event.listens_for(pool, "checkout")
    def on_checkout(dbapi_conn, connection_record, connection_proxy):
        """Track connection checkouts."""
        sqlalchemy_pool_checkouts.labels(pool_name=pool_name).inc()

        # Record checkout time for duration measurement
        connection_record.info["checkout_time"] = time.time()

    @event.listens_for(pool, "checkin")
    def on_checkin(dbapi_conn, connection_record):
        """Track connection checkins and duration."""
        sqlalchemy_pool_checkins.labels(pool_name=pool_name).inc()

        # Calculate checkout duration
        if "checkout_time" in connection_record.info:
            checkout_time = connection_record.info.pop("checkout_time")
            duration = time.time() - checkout_time
            sqlalchemy_pool_checkout_duration.labels(pool_name=pool_name).observe(duration)

    @event.listens_for(pool, "invalidate")
    def on_invalidate(dbapi_conn, connection_record, exception):
        """Track connection invalidations."""
        sqlalchemy_pool_invalidations.labels(pool_name=pool_name).inc()
        logger.warning(
            f"Pool '{pool_name}': Connection invalidated",
            extra={"exception": str(exception) if exception else None},
        )

    logger.info(f"SQLAlchemy pool metrics configured for '{pool_name}'")


def update_sqlalchemy_pool_metrics(engine: Engine, pool_name: str = "default"):
    """
    Update current state metrics for SQLAlchemy connection pool.
    Call this periodically (e.g., every 15 seconds) to keep metrics current.

    Args:
        engine: SQLAlchemy Engine instance
        pool_name: Name for the pool in metrics labels
    """
    try:
        pool = engine.pool

        # Update gauge metrics
        sqlalchemy_pool_size.labels(pool_name=pool_name).set(pool.size())
        sqlalchemy_pool_checked_in.labels(pool_name=pool_name).set(pool.checkedin())
        sqlalchemy_pool_checked_out.labels(pool_name=pool_name).set(pool.checkedout())
        sqlalchemy_pool_overflow.labels(pool_name=pool_name).set(pool.overflow())

        # Get waiters count if available (QueuePool specific)
        if hasattr(pool, "_waiters"):
            sqlalchemy_pool_waiters.labels(pool_name=pool_name).set(len(pool._waiters))

    except Exception as e:
        logger.error(f"Error updating SQLAlchemy pool metrics: {e}")


# ==================== PgBouncer Metrics Collection ====================


def collect_pgbouncer_metrics(
    pgbouncer_host: str = "pgbouncer",
    pgbouncer_port: int = 5432,
    pgbouncer_user: str = "trader",
    pgbouncer_password: str = "",
    database: str = "pgbouncer",
):
    """
    Collect metrics from PgBouncer's SHOW STATS and SHOW POOLS commands.

    Args:
        pgbouncer_host: PgBouncer hostname
        pgbouncer_port: PgBouncer port
        pgbouncer_user: PgBouncer admin user
        pgbouncer_password: User password
        database: Special "pgbouncer" database for admin queries
    """
    try:
        # Connect to PgBouncer admin console
        conn_string = (
            f"host={pgbouncer_host} port={pgbouncer_port} "
            f"user={pgbouncer_user} password={pgbouncer_password} "
            f"dbname={database}"
        )

        # PgBouncer admin console does not allow transactions; use autocommit
        with psycopg.connect(conn_string, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Get database stats
                cur.execute("SHOW DATABASES")
                columns = [desc[0] for desc in cur.description]
                for row in cur.fetchall():
                    db_stats = dict(zip(columns, row))
                    db_name = db_stats.get("name")

                    if db_name and db_name not in ("pgbouncer", ""):
                        pgbouncer_databases_current_connections.labels(database=db_name).set(
                            db_stats.get("current_connections", 0)
                        )

                        pgbouncer_databases_pool_size.labels(database=db_name).set(
                            db_stats.get("pool_size", 0)
                        )

                # Get pool stats
                cur.execute("SHOW POOLS")
                columns = [desc[0] for desc in cur.description]
                for row in cur.fetchall():
                    pool_stats = dict(zip(columns, row))
                    db_name = pool_stats.get("database")
                    user_name = pool_stats.get("user")

                    if db_name and db_name not in ("pgbouncer", ""):
                        labels = {"database": db_name, "user": user_name}

                        pgbouncer_pools_cl_active.labels(**labels).set(
                            pool_stats.get("cl_active", 0)
                        )
                        pgbouncer_pools_cl_waiting.labels(**labels).set(
                            pool_stats.get("cl_waiting", 0)
                        )
                        pgbouncer_pools_sv_active.labels(**labels).set(
                            pool_stats.get("sv_active", 0)
                        )
                        pgbouncer_pools_sv_idle.labels(**labels).set(pool_stats.get("sv_idle", 0))
                        pgbouncer_pools_sv_used.labels(**labels).set(pool_stats.get("sv_used", 0))
                        pgbouncer_pools_sv_tested.labels(**labels).set(
                            pool_stats.get("sv_tested", 0)
                        )
                        pgbouncer_pools_sv_login.labels(**labels).set(pool_stats.get("sv_login", 0))
                        pgbouncer_pools_maxwait.labels(**labels).set(pool_stats.get("maxwait", 0))

        logger.debug("PgBouncer metrics collected successfully")

    except Exception as e:
        logger.error(f"Error collecting PgBouncer metrics: {e}")


# ==================== Convenience Context Manager ====================


@contextmanager
def monitored_connection(engine: Engine, operation: str = "query"):
    """
    Context manager for monitoring database connection checkout duration.

    Usage:
        with monitored_connection(engine, "fetch_candles") as conn:
            result = conn.execute(query)

    Args:
        engine: SQLAlchemy Engine
        operation: Name of the operation for logging
    """
    start_time = time.time()
    connection = None

    try:
        connection = engine.connect()
        yield connection
    finally:
        duration = time.time() - start_time

        if connection:
            connection.close()

        logger.debug(
            f"Database operation '{operation}' completed",
            extra={"duration_seconds": duration},
        )


# ==================== Health Check ====================


def check_pool_health(engine: Engine, pool_name: str = "default") -> dict[str, Any]:
    """
    Check connection pool health and return status.

    Returns:
        Dictionary with pool health information
    """
    try:
        pool = engine.pool

        size = pool.size()
        checked_out = pool.checkedout()
        overflow = pool.overflow()

        # Calculate pool utilization
        total_capacity = pool._pool.maxsize + pool._max_overflow
        current_usage = checked_out + overflow
        utilization = (current_usage / total_capacity * 100) if total_capacity > 0 else 0

        # Determine health status
        if utilization >= 90:
            status = "critical"
        elif utilization >= 75:
            status = "warning"
        else:
            status = "healthy"

        return {
            "pool_name": pool_name,
            "status": status,
            "size": size,
            "checked_out": checked_out,
            "checked_in": pool.checkedin(),
            "overflow": overflow,
            "utilization_percent": round(utilization, 2),
            "total_capacity": total_capacity,
        }

    except Exception as e:
        logger.error(f"Error checking pool health: {e}")
        return {"pool_name": pool_name, "status": "error", "error": str(e)}
