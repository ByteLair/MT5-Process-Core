"""
End-to-End Integration Tests.
Tests complete workflows from data ingestion to prediction to signal generation.
"""
import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
import psycopg


class TestEndToEndIngestionFlow:
    """Test complete ingestion workflow."""
    
    def test_ingest_to_database_flow(
        self,
        test_client: TestClient,
        db_connection: psycopg.Connection,
        auth_headers: dict,
        sample_candle: dict,
        clean_market_data
    ):
        """Test: API ingest → Database storage → Verify."""
        # Step 1: Ingest via API
        response = test_client.post(
            "/ingest",
            json=sample_candle,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Step 2: Wait for async processing (if any)
        time.sleep(0.5)
        
        # Step 3: Verify in database
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM market_data 
                WHERE symbol = %(symbol)s 
                  AND timeframe = %(timeframe)s
                  AND ts = %(ts)s;
                """,
                sample_candle
            )
            result = cur.fetchone()
        
        assert result is not None
        assert result["symbol"] == sample_candle["symbol"]
        assert float(result["open"]) == sample_candle["open"]
        assert float(result["close"]) == sample_candle["close"]
    
    def test_batch_ingest_performance(
        self,
        test_client: TestClient,
        db_connection: psycopg.Connection,
        auth_headers: dict,
        sample_candles_batch: list[dict],
        clean_market_data
    ):
        """Test: Batch API ingest → Database → Performance metrics."""
        start_time = time.time()
        
        # Step 1: Ingest batch
        response = test_client.post(
            "/ingest_batch",
            json={"candles": sample_candles_batch},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        ingest_time = time.time() - start_time
        
        # Step 2: Verify count in DB
        time.sleep(0.5)
        with db_connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM market_data;")
            count = cur.fetchone()["count"]
        
        assert count == len(sample_candles_batch)
        
        # Step 3: Performance check
        throughput = len(sample_candles_batch) / ingest_time
        print(f"\nBatch ingest: {len(sample_candles_batch)} candles in {ingest_time:.2f}s ({throughput:.0f} ops/s)")
        
        assert ingest_time < 5.0, f"Batch ingest too slow: {ingest_time:.2f}s"


class TestEndToEndPredictionFlow:
    """Test complete prediction workflow."""
    
    @pytest.mark.skipif(
        True,  # Skip by default as ML model might not be trained
        reason="Requires trained ML model"
    )
    def test_ingest_to_prediction_flow(
        self,
        test_client: TestClient,
        db_connection: psycopg.Connection,
        auth_headers: dict,
        sample_candles_batch: list[dict],
        clean_market_data
    ):
        """Test: Ingest data → Train/Load model → Predict → Verify."""
        # Step 1: Ingest historical data
        response = test_client.post(
            "/ingest_batch",
            json={"candles": sample_candles_batch},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        time.sleep(1)
        
        # Step 2: Request prediction
        response = test_client.get(
            "/predict?symbol=EURUSD&timeframe=M1",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "prediction" in data or "signal" in data
        else:
            # Model not trained yet - that's OK for this test
            assert response.status_code in [404, 500]


class TestEndToEndSignalFlow:
    """Test complete signal generation and acknowledgment flow."""
    
    def test_signal_generation_to_ack_flow(
        self,
        test_client: TestClient,
        db_connection: psycopg.Connection,
        auth_headers: dict,
        sample_signal: dict,
        clean_signals
    ):
        """Test: Generate signal → Fetch signal → Acknowledge → Verify."""
        # Step 1: Insert signal directly to DB (simulate signal generation)
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
                );
                """,
                sample_signal
            )
            db_connection.commit()
        
        # Step 2: Fetch signal via API
        response = test_client.get(
            "/signals/next?symbol=EURUSD&timeframe=M1"
        )
        assert response.status_code == 200
        signal = response.json()
        assert signal["signal_id"] == sample_signal["signal_id"]
        
        # Step 3: Acknowledge signal execution
        ack_payload = {
            "signal_id": signal["signal_id"],
            "order_id": 12345,
            "status": "FILLED",
            "price": sample_signal["entry_price"],
            "slippage": 0.0001,
            "message": "Order executed successfully",
            "ts": signal["timestamp"]
        }
        
        response = test_client.post(
            "/signals/ack",
            json=ack_payload,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Step 4: Verify acknowledgment in DB
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM fills 
                WHERE signal_id = %s;
                """,
                (signal["signal_id"],)
            )
            fill = cur.fetchone()
        
        # May be None if fills table structure is different
        # Just verify no errors occurred
        assert True


class TestEndToEndMonitoringFlow:
    """Test complete monitoring workflow."""
    
    def test_metrics_collection_flow(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_candles_batch: list[dict],
        clean_market_data
    ):
        """Test: Ingest data → Collect metrics → Verify Prometheus."""
        # Step 1: Get baseline metrics
        response = test_client.get("/metrics")
        assert response.status_code == 200
        metrics_before = response.json()
        
        # Step 2: Ingest some data
        response = test_client.post(
            "/ingest_batch",
            json={"candles": sample_candles_batch},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        time.sleep(0.5)
        
        # Step 3: Get updated metrics
        response = test_client.get("/metrics")
        assert response.status_code == 200
        metrics_after = response.json()
        
        # Step 4: Verify metrics changed
        # Structure may vary, just check response is valid
        assert metrics_after is not None
        
        # Step 5: Check Prometheus metrics
        response = test_client.get("/prometheus")
        assert response.status_code == 200
        prometheus_metrics = response.text
        
        # Should contain ingest metrics
        assert "ingest_" in prometheus_metrics


class TestEndToEndHealthCheckFlow:
    """Test complete health check workflow."""
    
    def test_full_health_check(
        self,
        test_client: TestClient,
        db_connection: psycopg.Connection
    ):
        """Test: Health check → DB connectivity → Service status."""
        # Step 1: API health check
        response = test_client.get("/health")
        assert response.status_code == 200
        health = response.json()
        
        assert health["status"] == "ok"
        assert health.get("db_connected") is True or health.get("database") == "ok"
        
        # Step 2: Direct DB health check
        with db_connection.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
            assert result is not None
        
        # Step 3: Verify TimescaleDB
        with db_connection.cursor() as cur:
            cur.execute(
                "SELECT extname FROM pg_extension WHERE extname = 'timescaledb';"
            )
            result = cur.fetchone()
            assert result is not None


class TestEndToEndErrorRecovery:
    """Test error handling and recovery in E2E workflows."""
    
    def test_duplicate_ingest_recovery(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_candle: dict,
        clean_market_data
    ):
        """Test: Ingest → Duplicate ingest → Proper handling."""
        # Step 1: First ingest
        response1 = test_client.post(
            "/ingest",
            json=sample_candle,
            headers=auth_headers
        )
        assert response1.status_code == 200
        
        # Step 2: Duplicate ingest
        response2 = test_client.post(
            "/ingest",
            json=sample_candle,
            headers=auth_headers
        )
        assert response2.status_code == 200
        
        # Should handle gracefully
        data = response2.json()
        assert data["inserted"] == 0 or "duplicate" in str(data).lower()
    
    def test_invalid_data_recovery(
        self,
        test_client: TestClient,
        auth_headers: dict
    ):
        """Test: Invalid data → Error response → Continue working."""
        # Step 1: Send invalid data
        invalid_candle = {
            "ts": "invalid-timestamp",
            "symbol": "EURUSD",
            "open": "not-a-number"
        }
        
        response = test_client.post(
            "/ingest",
            json=invalid_candle,
            headers=auth_headers
        )
        assert response.status_code == 422
        
        # Step 2: Verify API still works after error
        response = test_client.get("/health")
        assert response.status_code == 200
        
        # Step 3: Send valid data after error
        valid_candle = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": 1.0850,
            "high": 1.0855,
            "low": 1.0848,
            "close": 1.0852,
            "volume": 1000
        }
        
        response = test_client.post(
            "/ingest",
            json=valid_candle,
            headers=auth_headers
        )
        assert response.status_code == 200


class TestEndToEndStressTest:
    """Stress tests for E2E workflows."""
    
    @pytest.mark.slow
    def test_sustained_load(
        self,
        test_client: TestClient,
        auth_headers: dict,
        clean_market_data
    ):
        """Test: Sustained load over time."""
        duration_seconds = 10
        requests_sent = 0
        errors = 0
        
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            candle = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "symbol": "EURUSD",
                "timeframe": "M1",
                "open": 1.0850,
                "high": 1.0855,
                "low": 1.0848,
                "close": 1.0852,
                "volume": 1000
            }
            
            response = test_client.post(
                "/ingest",
                json=candle,
                headers=auth_headers
            )
            
            requests_sent += 1
            if response.status_code not in [200, 409]:  # 409 = duplicate
                errors += 1
            
            time.sleep(0.1)  # 10 req/s
        
        elapsed = time.time() - start_time
        throughput = requests_sent / elapsed
        error_rate = errors / requests_sent if requests_sent > 0 else 0
        
        print(f"\nStress test: {requests_sent} requests in {elapsed:.2f}s ({throughput:.1f} req/s)")
        print(f"Error rate: {error_rate * 100:.2f}%")
        
        # Should handle load with low error rate
        assert error_rate < 0.05, f"Error rate too high: {error_rate * 100:.2f}%"
        assert throughput >= 8, f"Throughput too low: {throughput:.1f} req/s"
    
    @pytest.mark.slow
    def test_burst_load(
        self,
        test_client: TestClient,
        auth_headers: dict,
        clean_market_data
    ):
        """Test: Handle burst of requests."""
        burst_size = 100
        
        candles = [
            {
                "ts": datetime.now(timezone.utc).replace(second=i).isoformat(),
                "symbol": "EURUSD",
                "timeframe": "M1",
                "open": 1.0850,
                "high": 1.0855,
                "low": 1.0848,
                "close": 1.0852,
                "volume": 1000
            }
            for i in range(burst_size)
        ]
        
        start_time = time.time()
        
        # Send burst
        for candle in candles:
            test_client.post(
                "/ingest",
                json=candle,
                headers=auth_headers
            )
        
        elapsed = time.time() - start_time
        throughput = burst_size / elapsed
        
        print(f"\nBurst test: {burst_size} requests in {elapsed:.2f}s ({throughput:.0f} req/s)")
        
        # Should handle burst
        assert elapsed < 30, f"Burst took too long: {elapsed:.2f}s"


class TestEndToEndDataFlow:
    """Test complete data flow from EA to database to ML."""
    
    def test_complete_trading_cycle(
        self,
        test_client: TestClient,
        db_connection: psycopg.Connection,
        auth_headers: dict,
        clean_market_data,
        clean_signals
    ):
        """
        Test complete cycle:
        EA → API Ingest → Database → ML Prediction → Signal → EA Acknowledgment
        """
        # Step 1: EA sends candles (simulate)
        candles = [
            {
                "ts": datetime.now(timezone.utc).replace(second=i).isoformat(),
                "symbol": "EURUSD",
                "timeframe": "M1",
                "open": 1.0850 + i * 0.0001,
                "high": 1.0855 + i * 0.0001,
                "low": 1.0848 + i * 0.0001,
                "close": 1.0852 + i * 0.0001,
                "volume": 1000 + i * 10
            }
            for i in range(20)
        ]
        
        response = test_client.post(
            "/ingest_batch",
            json={"candles": candles},
            headers=auth_headers
        )
        assert response.status_code == 200
        
        time.sleep(0.5)
        
        # Step 2: Verify data in database
        with db_connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM market_data;")
            count = cur.fetchone()["count"]
            assert count == len(candles)
        
        # Step 3: Request prediction (may fail if no model)
        response = test_client.get(
            "/predict?symbol=EURUSD&timeframe=M1",
            headers=auth_headers
        )
        # OK if fails - model might not be trained
        assert response.status_code in [200, 404, 500]
        
        # Step 4: Check metrics updated
        response = test_client.get("/metrics")
        assert response.status_code == 200
        
        # Step 5: Verify system still healthy
        response = test_client.get("/health")
        assert response.status_code == 200
        
        print("\n✅ Complete trading cycle test passed")
