import os
from typing import Any


def get_db_url() -> str:
    """
    Get database URL from environment.

    By default uses PgBouncer on port 6432 for connection pooling.
    Set USE_PGBOUNCER=false to connect directly to PostgreSQL.
    """
    use_pgbouncer = os.getenv("USE_PGBOUNCER", "true").lower() == "true"

    if use_pgbouncer:
        # Connect via PgBouncer (transaction pooling)
        return os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://trader:trader123@pgbouncer:5432/mt5_trading",
        )
    else:
        # Direct connection to PostgreSQL
        return os.getenv(
            "DATABASE_URL", "postgresql+psycopg://trader:trader123@db:5432/mt5_trading"
        )


def get_sqlalchemy_pool_config() -> dict[str, Any]:
    """
    Get optimized SQLAlchemy connection pool configuration.

    When using PgBouncer:
    - Smaller pool_size since PgBouncer handles pooling
    - Lower max_overflow to prevent overwhelming PgBouncer
    - Shorter pool_timeout for faster failure detection

    Without PgBouncer:
    - Larger pool_size for direct PostgreSQL connections
    - Higher max_overflow for burst capacity
    """
    use_pgbouncer = os.getenv("USE_PGBOUNCER", "true").lower() == "true"

    if use_pgbouncer:
        # Optimized for PgBouncer transaction pooling
        return {
            # Core pool size - keep small, PgBouncer does the heavy lifting
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            # Additional connections for burst traffic
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            # How long to wait for connection (seconds)
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "10")),
            # Recycle connections after 30 minutes
            # PgBouncer handles server-side recycling, this is client-side
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
            # Check connection health before using
            "pool_pre_ping": os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
            # Pool class - QueuePool is default and best for most cases
            # "pool_class": QueuePool,  # Default, no need to specify
            # Echo pool events for debugging (disable in production)
            "echo_pool": os.getenv("DB_ECHO_POOL", "false").lower() == "true",
        }
    else:
        # Optimized for direct PostgreSQL connection
        return {
            # Larger pool for direct connections
            "pool_size": int(os.getenv("DB_POOL_SIZE", "20")),
            # More overflow capacity
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "30")),
            # Longer timeout for direct connections
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            # Recycle connections after 1 hour
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
            # Always pre-ping without PgBouncer
            "pool_pre_ping": True,
            "echo_pool": os.getenv("DB_ECHO_POOL", "false").lower() == "true",
        }


def get_db_connect_args() -> dict[str, Any]:
    """
    Get psycopg connection arguments for optimal performance.
    """
    return {
        # Prepare threshold - use server-side prepared statements
        # -1 disables (good for transaction pooling)
        # >0 enables after N executions (good for session pooling)
        "prepare_threshold": int(os.getenv("DB_PREPARE_THRESHOLD", "0")),
        # Connection timeout
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
        # TCP keepalive
        "keepalives": 1,
        "keepalives_idle": 60,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        # Application name for monitoring
        "application_name": os.getenv("APP_NAME", "mt5-trading-api"),
    }
