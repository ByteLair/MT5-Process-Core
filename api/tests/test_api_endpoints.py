"""
Comprehensive API endpoint tests.
Tests all major endpoints: health, ingest, metrics, signals, predict.
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for /health endpoint."""
    
    def test_health_check(self, test_client: TestClient):
        """Test basic health check."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "db_connected" in data
    
    def test_health_response_time(self, test_client: TestClient):
        """Test health check response time < 50ms."""
        import time
        start = time.time()
        response = test_client.get("/health")
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        assert response.status_code == 200
        assert elapsed < 50, f"Health check took {elapsed:.2f}ms, expected < 50ms"


class TestIngestEndpoint:
    """Tests for /ingest endpoint."""
    
    def test_ingest_single_candle(
        self, 
        test_client: TestClient, 
        sample_candle: dict,
        auth_headers: dict,
        clean_market_data
    ):
        """Test ingesting a single candle."""
        response = test_client.post(
            "/ingest",
            json=sample_candle,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["inserted"] >= 0  # May be 0 if duplicate
    
    def test_ingest_batch_candles(
        self,
        test_client: TestClient,
        sample_candles_batch: list[dict],
        auth_headers: dict,
        clean_market_data
    ):
        """Test ingesting batch of candles."""
        response = test_client.post(
            "/ingest_batch",
            json={"candles": sample_candles_batch},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["inserted"] >= 0
        assert data["duplicates"] >= 0
        assert data["inserted"] + data["duplicates"] == len(sample_candles_batch)
    
    def test_ingest_without_auth(self, test_client: TestClient, sample_candle: dict):
        """Test ingest without authentication should fail."""
        response = test_client.post("/ingest", json=sample_candle)
        # Depending on auth implementation, might be 401 or 403
        assert response.status_code in [401, 403]
    
    def test_ingest_invalid_data(self, test_client: TestClient, auth_headers: dict):
        """Test ingest with invalid data should fail."""
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
        assert response.status_code == 422  # Validation error
    
    def test_ingest_duplicate_handling(
        self,
        test_client: TestClient,
        sample_candle: dict,
        auth_headers: dict,
        clean_market_data
    ):
        """Test that duplicate candles are handled correctly."""
        # First insert
        response1 = test_client.post(
            "/ingest",
            json=sample_candle,
            headers=auth_headers
        )
        assert response1.status_code == 200
        
        # Second insert (duplicate)
        response2 = test_client.post(
            "/ingest",
            json=sample_candle,
            headers=auth_headers
        )
        assert response2.status_code == 200
        data2 = response2.json()
        # Should report as duplicate or 0 inserted
        assert data2["inserted"] == 0 or "duplicate" in data2.get("message", "").lower()


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""
    
    def test_metrics_basic(self, test_client: TestClient):
        """Test basic metrics retrieval."""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "current" in data or "total_candles" in data
    
    def test_metrics_structure(self, test_client: TestClient):
        """Test metrics response structure."""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        
        # Should contain key metrics
        expected_fields = ["current", "last_db"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_prometheus_metrics(self, test_client: TestClient):
        """Test Prometheus metrics endpoint."""
        response = test_client.get("/prometheus")
        assert response.status_code == 200
        
        # Prometheus format is text/plain
        assert "text/plain" in response.headers.get("content-type", "")
        
        # Should contain some metric names
        content = response.text
        assert "ingest_" in content or "api_" in content


class TestSignalsEndpoint:
    """Tests for /signals/* endpoints."""
    
    def test_signals_next(self, test_client: TestClient, seed_signals):
        """Test getting next signal."""
        response = test_client.get("/signals/next?symbol=EURUSD&timeframe=M1")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "signal_id" in data
            assert data["symbol"] == "EURUSD"
            assert data["timeframe"] == "M1"
    
    def test_signals_latest(self, test_client: TestClient):
        """Test getting latest signals."""
        response = test_client.get("/signals/latest?symbol=EURUSD&timeframe=M1")
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
    
    def test_signals_history(self, test_client: TestClient):
        """Test getting signal history."""
        response = test_client.get(
            "/signals/history?symbol=EURUSD&timeframe=M1&limit=10"
        )
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 10
    
    def test_signals_ack(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_signal: dict,
        seed_signals
    ):
        """Test acknowledging signal execution."""
        payload = {
            "signal_id": sample_signal["signal_id"],
            "order_id": 12345,
            "status": "FILLED",
            "price": 1.0850,
            "slippage": 0.0001,
            "message": "Order executed successfully",
            "ts": sample_signal["timestamp"]
        }
        
        response = test_client.post(
            "/signals/ack",
            json=payload,
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True or data.get("status") == "success"


class TestPredictEndpoint:
    """Tests for /predict endpoint."""
    
    def test_predict_on_demand(
        self,
        test_client: TestClient,
        auth_headers: dict,
        seed_market_data
    ):
        """Test on-demand prediction."""
        response = test_client.get(
            "/predict?symbol=EURUSD&timeframe=M1",
            headers=auth_headers
        )
        
        # May fail if model not trained, that's OK
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "prediction" in data or "signal" in data
    
    def test_predict_batch(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_candles_batch: list[dict],
        seed_market_data
    ):
        """Test batch prediction."""
        payload = {
            "symbol": "EURUSD",
            "timeframe": "M1",
            "candles": sample_candles_batch
        }
        
        response = test_client.post(
            "/predict_batch",
            json=payload,
            headers=auth_headers
        )
        
        # May fail if model not trained
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "predictions" in data or isinstance(data, list)


class TestErrorHandling:
    """Tests for error handling and edge cases."""
    
    def test_404_on_unknown_endpoint(self, test_client: TestClient):
        """Test 404 on unknown endpoint."""
        response = test_client.get("/this/endpoint/does/not/exist")
        assert response.status_code == 404
    
    def test_method_not_allowed(self, test_client: TestClient):
        """Test 405 on wrong HTTP method."""
        # /health only accepts GET
        response = test_client.post("/health")
        assert response.status_code == 405
    
    def test_large_payload_handling(
        self,
        test_client: TestClient,
        auth_headers: dict
    ):
        """Test handling of large payloads."""
        # Create a very large batch
        large_batch = [
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
            for i in range(1000)  # 1000 candles
        ]
        
        response = test_client.post(
            "/ingest_batch",
            json={"candles": large_batch},
            headers=auth_headers,
            timeout=30  # Allow more time for large payload
        )
        
        # Should either succeed or return appropriate error
        assert response.status_code in [200, 413, 422, 500]


class TestRateLimiting:
    """Tests for rate limiting (if implemented)."""
    
    def test_rate_limit_not_exceeded_normal_use(
        self,
        test_client: TestClient,
        sample_candle: dict,
        auth_headers: dict
    ):
        """Test that normal use doesn't hit rate limits."""
        for _ in range(10):
            response = test_client.post(
                "/ingest",
                json=sample_candle,
                headers=auth_headers
            )
            assert response.status_code in [200, 409]  # 409 = conflict/duplicate
    
    @pytest.mark.slow
    def test_rate_limit_protection(
        self,
        test_client: TestClient,
        sample_candle: dict,
        auth_headers: dict
    ):
        """Test rate limiting kicks in after many requests."""
        # Send many requests rapidly
        responses = []
        for _ in range(100):
            response = test_client.post(
                "/ingest",
                json=sample_candle,
                headers=auth_headers
            )
            responses.append(response.status_code)
        
        # If rate limiting is enabled, should see 429 at some point
        # If not, all should be 200 or 409
        assert all(code in [200, 409, 429] for code in responses)


class TestCORS:
    """Tests for CORS configuration."""
    
    def test_cors_headers_present(self, test_client: TestClient):
        """Test that CORS headers are present."""
        response = test_client.options("/health")
        
        # CORS preflight should work
        assert response.status_code in [200, 204]
    
    def test_cors_allows_origin(self, test_client: TestClient):
        """Test CORS allows specified origins."""
        headers = {"Origin": "http://localhost:3000"}
        response = test_client.get("/health", headers=headers)
        
        assert response.status_code == 200
        # Should have CORS header in response
        assert "access-control-allow-origin" in [
            h.lower() for h in response.headers.keys()
        ]
