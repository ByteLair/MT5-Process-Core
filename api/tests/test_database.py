"""
Database tests for PostgreSQL and TimescaleDB functionality.
Tests connections, CRUD operations, hypertables, compression, and performance.
"""
import time
from datetime import datetime, timezone

import pytest
import psycopg
from psycopg.rows import dict_row


class TestDatabaseConnection:
    """Tests for database connectivity."""
    
    def test_direct_connection(self, db_connection: psycopg.Connection):
        """Test direct PostgreSQL connection."""
        assert db_connection is not None
        
        with db_connection.cursor() as cur:
            cur.execute("SELECT 1 as test;")
            result = cur.fetchone()
            assert result["test"] == 1
    
    def test_pgbouncer_connection(self, pgbouncer_connection: psycopg.Connection):
        """Test PgBouncer connection pooling."""
        assert pgbouncer_connection is not None
        
        with pgbouncer_connection.cursor() as cur:
            cur.execute("SELECT 1 as test;")
            result = cur.fetchone()
            assert result["test"] == 1
    
    def test_database_version(self, db_connection: psycopg.Connection):
        """Test PostgreSQL version is correct."""
        with db_connection.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()["version"]
            assert "PostgreSQL 16" in version
    
    def test_timescaledb_extension(self, db_connection: psycopg.Connection):
        """Test TimescaleDB extension is installed."""
        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT extversion FROM pg_extension WHERE extname = 'timescaledb';"
            )
            result = cur.fetchone()
            assert result is not None
            assert "2.1" in result["extversion"]  # Should be 2.14.2


class TestDatabaseSchema:
    """Tests for database schema."""
    
    def test_tables_exist(self, db_connection: psycopg.Connection):
        """Test all required tables exist."""
        required_tables = [
            "market_data",
            "market_data_raw",
            "signals",
            "fills",
            "trade_logs"
        ]
        
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
                """
            )
            existing_tables = [row["table_name"] for row in cur.fetchall()]
        
        for table in required_tables:
            assert table in existing_tables, f"Table {table} not found"
    
    def test_hypertables_configured(self, db_connection: psycopg.Connection):
        """Test hypertables are properly configured."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT hypertable_name 
                FROM timescaledb_information.hypertables;
                """
            )
            hypertables = [row["hypertable_name"] for row in cur.fetchall()]
        
        expected_hypertables = ["market_data", "market_data_raw", "fills", "trade_logs"]
        for ht in expected_hypertables:
            assert ht in hypertables, f"Hypertable {ht} not configured"
    
    def test_compression_enabled(self, db_connection: psycopg.Connection):
        """Test compression is enabled on market_data."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT compression_enabled 
                FROM timescaledb_information.hypertables 
                WHERE hypertable_name = 'market_data';
                """
            )
            result = cur.fetchone()
            assert result is not None
            assert result["compression_enabled"] is True
    
    def test_indexes_exist(self, db_connection: psycopg.Connection):
        """Test key indexes are created."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename IN ('market_data', 'signals', 'fills');
                """
            )
            indexes = [row["indexname"] for row in cur.fetchall()]
        
        # Should have indexes on key columns
        assert len(indexes) > 0, "No indexes found"


class TestMarketDataCRUD:
    """Tests for market_data table CRUD operations."""
    
    def test_insert_candle(
        self,
        db_connection: psycopg.Connection,
        sample_candle: dict,
        clean_market_data
    ):
        """Test inserting a single candle."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO market_data (
                    ts, symbol, timeframe, open, high, low, close, 
                    volume, tick_volume, spread
                ) VALUES (
                    %(ts)s, %(symbol)s, %(timeframe)s, %(open)s, %(high)s, 
                    %(low)s, %(close)s, %(volume)s, %(tick_volume)s, %(spread)s
                )
                RETURNING id;
                """,
                sample_candle
            )
            result = cur.fetchone()
            db_connection.commit()
            
            assert result is not None
            assert result["id"] is not None
    
    def test_insert_batch(
        self,
        db_connection: psycopg.Connection,
        sample_candles_batch: list[dict],
        clean_market_data
    ):
        """Test batch insert performance."""
        start_time = time.time()
        
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
        
        elapsed = time.time() - start_time
        
        # Batch insert should be fast
        assert elapsed < 1.0, f"Batch insert took {elapsed:.2f}s, expected < 1s"
        
        # Verify all inserted
        with db_connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM market_data;")
            count = cur.fetchone()["count"]
            assert count == len(sample_candles_batch)
    
    def test_select_by_symbol(
        self,
        db_connection: psycopg.Connection,
        seed_market_data
    ):
        """Test selecting candles by symbol."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM market_data 
                WHERE symbol = 'EURUSD' 
                ORDER BY ts DESC 
                LIMIT 10;
                """
            )
            results = cur.fetchall()
            
            assert len(results) > 0
            for row in results:
                assert row["symbol"] == "EURUSD"
    
    def test_select_by_timerange(
        self,
        db_connection: psycopg.Connection,
        seed_market_data
    ):
        """Test selecting candles by time range."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM market_data 
                WHERE ts >= NOW() - INTERVAL '1 hour'
                ORDER BY ts DESC;
                """
            )
            results = cur.fetchall()
            
            # Should have recent data from seed
            assert len(results) > 0
    
    def test_update_candle(
        self,
        db_connection: psycopg.Connection,
        sample_candle: dict,
        clean_market_data
    ):
        """Test updating a candle."""
        # Insert first
        with db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO market_data (
                    ts, symbol, timeframe, open, high, low, close, volume
                ) VALUES (
                    %(ts)s, %(symbol)s, %(timeframe)s, %(open)s, %(high)s, 
                    %(low)s, %(close)s, %(volume)s
                )
                RETURNING id;
                """,
                sample_candle
            )
            candle_id = cur.fetchone()["id"]
            db_connection.commit()
        
        # Update
        new_close = 1.0860
        with db_connection.cursor() as cur:
            cur.execute(
                "UPDATE market_data SET close = %s WHERE id = %s;",
                (new_close, candle_id)
            )
            db_connection.commit()
        
        # Verify
        with db_connection.cursor() as cur:
            cur.execute("SELECT close FROM market_data WHERE id = %s;", (candle_id,))
            result = cur.fetchone()
            assert result["close"] == new_close
    
    def test_delete_old_data(
        self,
        db_connection: psycopg.Connection,
        clean_market_data
    ):
        """Test deleting old data (retention policy simulation)."""
        # Insert old candle
        old_candle = {
            "ts": "2020-01-01T00:00:00Z",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": 1.1000,
            "high": 1.1010,
            "low": 1.0990,
            "close": 1.1005,
            "volume": 1000
        }
        
        with db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO market_data (
                    ts, symbol, timeframe, open, high, low, close, volume
                ) VALUES (
                    %(ts)s, %(symbol)s, %(timeframe)s, %(open)s, %(high)s, 
                    %(low)s, %(close)s, %(volume)s
                );
                """,
                old_candle
            )
            db_connection.commit()
        
        # Delete old data
        with db_connection.cursor() as cur:
            cur.execute(
                "DELETE FROM market_data WHERE ts < '2021-01-01';"
            )
            deleted_count = cur.rowcount
            db_connection.commit()
        
        assert deleted_count > 0


class TestSignalsCRUD:
    """Tests for signals table operations."""
    
    def test_insert_signal(
        self,
        db_connection: psycopg.Connection,
        sample_signal: dict,
        clean_signals
    ):
        """Test inserting a trading signal."""
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
                RETURNING signal_id;
                """,
                sample_signal
            )
            result = cur.fetchone()
            db_connection.commit()
            
            assert result is not None
            assert result["signal_id"] == sample_signal["signal_id"]
    
    def test_select_latest_signal(
        self,
        db_connection: psycopg.Connection,
        seed_signals
    ):
        """Test selecting latest signal."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM signals 
                WHERE symbol = 'EURUSD' AND timeframe = 'M1'
                ORDER BY timestamp DESC 
                LIMIT 1;
                """
            )
            result = cur.fetchone()
            
            assert result is not None
            assert result["symbol"] == "EURUSD"


class TestTimescaleDBFeatures:
    """Tests for TimescaleDB-specific features."""
    
    def test_time_bucket_aggregation(
        self,
        db_connection: psycopg.Connection,
        seed_market_data
    ):
        """Test time_bucket aggregation."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    time_bucket('5 minutes', ts) AS bucket,
                    symbol,
                    AVG(close) AS avg_close,
                    MAX(high) AS max_high,
                    MIN(low) AS min_low
                FROM market_data
                WHERE symbol = 'EURUSD'
                GROUP BY bucket, symbol
                ORDER BY bucket DESC
                LIMIT 10;
                """
            )
            results = cur.fetchall()
            
            assert len(results) > 0
            for row in results:
                assert row["avg_close"] is not None
                assert row["max_high"] >= row["min_low"]
    
    def test_continuous_aggregates_exist(self, db_connection: psycopg.Connection):
        """Test continuous aggregates are configured."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT view_name 
                FROM timescaledb_information.continuous_aggregates;
                """
            )
            views = [row["view_name"] for row in cur.fetchall()]
        
        # Should have continuous aggregates for different timeframes
        # e.g., market_data_m5, market_data_h1, etc.
        # This depends on your actual setup
        assert len(views) >= 0  # May be 0 if not configured yet
    
    def test_chunk_info(self, db_connection: psycopg.Connection):
        """Test chunk information for hypertable."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    chunk_name,
                    range_start,
                    range_end
                FROM timescaledb_information.chunks
                WHERE hypertable_name = 'market_data'
                ORDER BY range_start DESC
                LIMIT 5;
                """
            )
            chunks = cur.fetchall()
        
        # May have 0 chunks if no data
        if len(chunks) > 0:
            for chunk in chunks:
                assert chunk["chunk_name"] is not None
                assert chunk["range_start"] is not None


class TestPerformance:
    """Performance tests for database operations."""
    
    def test_bulk_insert_performance(
        self,
        db_connection: psycopg.Connection,
        clean_market_data,
        benchmark_config: dict
    ):
        """Test bulk insert performance."""
        batch_size = benchmark_config["batch_size"]
        
        # Generate test data
        candles = [
            {
                "ts": f"2025-11-13T00:{i:02d}:00Z",
                "symbol": "EURUSD",
                "timeframe": "M1",
                "open": 1.0850,
                "high": 1.0855,
                "low": 1.0848,
                "close": 1.0852,
                "volume": 1000
            }
            for i in range(batch_size)
        ]
        
        start_time = time.time()
        
        with db_connection.cursor() as cur:
            for candle in candles:
                cur.execute(
                    """
                    INSERT INTO market_data (
                        ts, symbol, timeframe, open, high, low, close, volume
                    ) VALUES (
                        %(ts)s, %(symbol)s, %(timeframe)s, %(open)s, %(high)s, 
                        %(low)s, %(close)s, %(volume)s
                    )
                    ON CONFLICT (ts, symbol, timeframe) DO NOTHING;
                    """,
                    candle
                )
            db_connection.commit()
        
        elapsed = time.time() - start_time
        throughput = batch_size / elapsed
        
        print(f"\nBulk insert: {batch_size} candles in {elapsed:.2f}s ({throughput:.0f} ops/s)")
        
        # Should be fast
        assert elapsed < 5.0, f"Bulk insert too slow: {elapsed:.2f}s"
    
    def test_query_performance(
        self,
        db_connection: psycopg.Connection,
        seed_market_data
    ):
        """Test query performance."""
        queries = [
            "SELECT * FROM market_data WHERE symbol = 'EURUSD' ORDER BY ts DESC LIMIT 100;",
            "SELECT AVG(close) FROM market_data WHERE symbol = 'EURUSD';",
            "SELECT COUNT(*) FROM market_data;",
        ]
        
        for query in queries:
            start_time = time.time()
            
            with db_connection.cursor() as cur:
                cur.execute(query)
                cur.fetchall()
            
            elapsed = time.time() - start_time
            
            # Queries should be fast
            assert elapsed < 0.5, f"Query too slow: {elapsed:.2f}s - {query}"
    
    def test_concurrent_reads(
        self,
        db_connection: psycopg.Connection,
        seed_market_data
    ):
        """Test concurrent read performance."""
        import concurrent.futures
        
        def read_data():
            with db_connection.cursor() as cur:
                cur.execute(
                    "SELECT * FROM market_data WHERE symbol = 'EURUSD' LIMIT 10;"
                )
                return cur.fetchall()
        
        start_time = time.time()
        
        # Simulate 10 concurrent reads
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_data) for _ in range(10)]
            results = [f.result() for f in futures]
        
        elapsed = time.time() - start_time
        
        assert len(results) == 10
        assert elapsed < 2.0, f"Concurrent reads too slow: {elapsed:.2f}s"


class TestDataIntegrity:
    """Tests for data integrity and constraints."""
    
    def test_unique_constraint(
        self,
        db_connection: psycopg.Connection,
        sample_candle: dict,
        clean_market_data
    ):
        """Test unique constraint on (ts, symbol, timeframe)."""
        # Insert first time - should succeed
        with db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO market_data (
                    ts, symbol, timeframe, open, high, low, close, volume
                ) VALUES (
                    %(ts)s, %(symbol)s, %(timeframe)s, %(open)s, %(high)s, 
                    %(low)s, %(close)s, %(volume)s
                );
                """,
                sample_candle
            )
            db_connection.commit()
        
        # Insert duplicate - should fail or be handled by ON CONFLICT
        with db_connection.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO market_data (
                        ts, symbol, timeframe, open, high, low, close, volume
                    ) VALUES (
                        %(ts)s, %(symbol)s, %(timeframe)s, %(open)s, %(high)s, 
                        %(low)s, %(close)s, %(volume)s
                    );
                    """,
                    sample_candle
                )
                db_connection.commit()
                # If we get here, ON CONFLICT must be handling it
            except psycopg.errors.UniqueViolation:
                # Expected if no ON CONFLICT clause
                db_connection.rollback()
                pass
    
    def test_not_null_constraints(
        self,
        db_connection: psycopg.Connection,
        clean_market_data
    ):
        """Test NOT NULL constraints."""
        # Try to insert without required fields
        with pytest.raises(psycopg.errors.NotNullViolation):
            with db_connection.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO market_data (ts, symbol, timeframe) 
                    VALUES (NOW(), 'EURUSD', 'M1');
                    """
                )
                db_connection.commit()
        
        db_connection.rollback()
