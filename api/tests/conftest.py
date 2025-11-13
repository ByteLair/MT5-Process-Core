"""
Test fixtures and configuration for pytest.
Provides reusable test data and database connections.
"""
import os
from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
import psycopg
from psycopg.rows import dict_row

from api.app.main import app


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_client() -> TestClient:
    """FastAPI test client for API endpoint testing."""
    return TestClient(app)


@pytest.fixture(scope="session")
def db_connection() -> Generator[psycopg.Connection, None, None]:
    """
    Database connection for direct DB tests.
    Uses session scope to reuse connection across tests.
    """
    conn = psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "mt5_trading"),
        user=os.getenv("POSTGRES_USER", "trader"),
        password=os.getenv("POSTGRES_PASSWORD", "trader123"),
        row_factory=dict_row
    )
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def pgbouncer_connection() -> Generator[psycopg.Connection, None, None]:
    """
    PgBouncer connection for pooling tests.
    """
    conn = psycopg.connect(
        host=os.getenv("PGBOUNCER_HOST", "pgbouncer"),
        port=int(os.getenv("PGBOUNCER_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "mt5_trading"),
        user=os.getenv("POSTGRES_USER", "trader"),
        password=os.getenv("POSTGRES_PASSWORD", "trader123"),
        row_factory=dict_row
    )
    yield conn
    conn.close()


@pytest.fixture
def sample_candle() -> dict:
    """Sample candle data for testing."""
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "symbol": "EURUSD",
        "timeframe": "M1",
        "open": 1.0850,
        "high": 1.0855,
        "low": 1.0848,
        "close": 1.0852,
        "volume": 1000,
        "tick_volume": 150,
        "spread": 2
    }


@pytest.fixture
def sample_candles_batch() -> list[dict]:
    """Batch of sample candles for testing."""
    base_ts = datetime.now(timezone.utc)
    return [
        {
            "ts": base_ts.replace(minute=i).isoformat(),
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": 1.0850 + i * 0.0001,
            "high": 1.0855 + i * 0.0001,
            "low": 1.0848 + i * 0.0001,
            "close": 1.0852 + i * 0.0001,
            "volume": 1000 + i * 10,
            "tick_volume": 150 + i,
            "spread": 2
        }
        for i in range(10)
    ]


@pytest.fixture
def sample_signal() -> dict:
    """Sample signal data for testing."""
    return {
        "signal_id": "test-signal-001",
        "symbol": "EURUSD",
        "timeframe": "M1",
        "signal_type": "BUY",
        "entry_price": 1.0850,
        "stop_loss": 1.0840,
        "take_profit": 1.0870,
        "confidence": 0.85,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def api_key() -> str:
    """API key for authenticated requests."""
    return os.getenv("API_KEY", "test_api_key_12345")


@pytest.fixture
def auth_headers(api_key: str) -> dict:
    """Headers with authentication."""
    return {"X-API-Key": api_key}


# ============================================================================
# Database cleanup fixtures
# ============================================================================

@pytest.fixture(scope="function")
def clean_market_data(db_connection: psycopg.Connection):
    """Clean market_data table after test."""
    yield
    with db_connection.cursor() as cur:
        cur.execute("TRUNCATE TABLE market_data CASCADE;")
        db_connection.commit()


@pytest.fixture(scope="function")
def clean_signals(db_connection: psycopg.Connection):
    """Clean signals table after test."""
    yield
    with db_connection.cursor() as cur:
        cur.execute("TRUNCATE TABLE signals CASCADE;")
        db_connection.commit()


@pytest.fixture(scope="function")
def clean_fills(db_connection: psycopg.Connection):
    """Clean fills table after test."""
    yield
    with db_connection.cursor() as cur:
        cur.execute("TRUNCATE TABLE fills CASCADE;")
        db_connection.commit()


# ============================================================================
# Test data seeding fixtures
# ============================================================================

@pytest.fixture
def seed_market_data(db_connection: psycopg.Connection, sample_candles_batch: list[dict]):
    """Seed database with sample market data."""
    with db_connection.cursor() as cur:
        for candle in sample_candles_batch:
            cur.execute(
                """
                INSERT INTO market_data (
                    ts, symbol, timeframe, open, high, low, close, 
                    volume, tick_volume, spread
                ) VALUES (
                    %(ts)s, %(symbol)s, %(timeframe)s, %(open)s, %(high)s, 
                    %(low)s, %(close)s, %(volume)s, %(tick_volume)s, %(spread)s
                )
                ON CONFLICT (ts, symbol, timeframe) DO NOTHING;
                """,
                candle
            )
        db_connection.commit()
    
    yield
    
    # Cleanup
    with db_connection.cursor() as cur:
        cur.execute("TRUNCATE TABLE market_data CASCADE;")
        db_connection.commit()


@pytest.fixture
def seed_signals(db_connection: psycopg.Connection, sample_signal: dict):
    """Seed database with sample signals."""
    with db_connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO signals (
                signal_id, symbol, timeframe, signal_type, entry_price,
                stop_loss, take_profit, confidence, timestamp
            ) VALUES (
                %(signal_id)s, %(symbol)s, %(timeframe)s, %(signal_type)s,
                %(entry_price)s, %(stop_loss)s, %(take_profit)s,
                %(confidence)s, %(timestamp)s
            )
            ON CONFLICT (signal_id) DO NOTHING;
            """,
            sample_signal
        )
        db_connection.commit()
    
    yield
    
    # Cleanup
    with db_connection.cursor() as cur:
        cur.execute("TRUNCATE TABLE signals CASCADE;")
        db_connection.commit()


# ============================================================================
# Performance testing fixtures
# ============================================================================

@pytest.fixture
def benchmark_config() -> dict:
    """Configuration for benchmark tests."""
    return {
        "max_latency_ms": 100,
        "max_throughput_req_per_sec": 1000,
        "batch_size": 100,
        "iterations": 10
    }
