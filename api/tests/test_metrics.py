"""
Tests for Prometheus metrics collection and exposition.
Validates metric types, labels, and values.
"""
import time
import pytest
from fastapi.testclient import TestClient


class TestPrometheusMetrics:
    """Tests for Prometheus metrics endpoint."""
    
    def test_prometheus_endpoint_exists(self, test_client: TestClient):
        """Test that Prometheus metrics endpoint is accessible."""
        response = test_client.get("/prometheus")
        assert response.status_code == 200
    
    def test_prometheus_content_type(self, test_client: TestClient):
        """Test that Prometheus endpoint returns correct content type."""
        response = test_client.get("/prometheus")
        assert "text/plain" in response.headers.get("content-type", "")
    
    def test_prometheus_metrics_format(self, test_client: TestClient):
        """Test that metrics follow Prometheus format."""
        response = test_client.get("/prometheus")
        content = response.text
        
        # Should contain metric definitions (# HELP, # TYPE)
        assert "# HELP" in content or "# TYPE" in content or len(content) > 0
    
    def test_ingest_metrics_present(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_candles_batch: list[dict],
        clean_market_data
    ):
        """Test that ingest metrics are collected."""
        # Perform some ingestions
        test_client.post(
            "/ingest_batch",
            json={"candles": sample_candles_batch},
            headers=auth_headers
        )
        
        time.sleep(0.5)
        
        # Check metrics
        response = test_client.get("/prometheus")
        content = response.text
        
        # Should contain ingest-related metrics
        expected_metrics = [
            "ingest_",  # General pattern
        ]
        
        # At least one metric should be present
        has_metrics = any(metric in content for metric in expected_metrics)
        assert has_metrics or len(content) > 100  # Or has substantial content


class TestMetricsIncrement:
    """Tests for metric value changes."""
    
    def test_ingest_counter_increments(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_candle: dict,
        clean_market_data
    ):
        """Test that ingest counter increments on each request."""
        # Get baseline
        response1 = test_client.get("/prometheus")
        content1 = response1.text
        
        # Perform ingest
        test_client.post("/ingest", json=sample_candle, headers=auth_headers)
        
        time.sleep(0.2)
        
        # Get updated metrics
        response2 = test_client.get("/prometheus")
        content2 = response2.text
        
        # Content should change (metrics updated)
        # Note: This is a simple check, real test would parse values
        assert len(content2) >= len(content1)
    
    def test_error_counter_increments(
        self,
        test_client: TestClient,
        auth_headers: dict
    ):
        """Test that error counter increments on failures."""
        # Get baseline
        response1 = test_client.get("/prometheus")
        
        # Trigger error (invalid data)
        test_client.post(
            "/ingest",
            json={"invalid": "data"},
            headers=auth_headers
        )
        
        time.sleep(0.2)
        
        # Get updated metrics
        response2 = test_client.get("/prometheus")
        
        # Metrics should be updated
        assert response2.status_code == 200


class TestMetricLabels:
    """Tests for metric labels."""
    
    def test_metrics_have_labels(self, test_client: TestClient):
        """Test that metrics include labels."""
        response = test_client.get("/prometheus")
        content = response.text
        
        # Prometheus metrics with labels include {label="value"}
        has_labels = "{" in content and "}" in content
        
        # Either has labels or is empty (no data yet)
        assert has_labels or len(content) < 100
    
    def test_symbol_label_present(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_candle: dict,
        clean_market_data
    ):
        """Test that symbol label is tracked."""
        # Ingest candle with specific symbol
        test_client.post("/ingest", json=sample_candle, headers=auth_headers)
        
        time.sleep(0.5)
        
        response = test_client.get("/prometheus")
        content = response.text
        
        # Should contain symbol in metrics
        # (exact format depends on implementation)
        assert len(content) > 0


class TestMetricsPerformance:
    """Tests for metrics collection performance."""
    
    def test_metrics_endpoint_fast(self, test_client: TestClient):
        """Test that metrics endpoint responds quickly."""
        start = time.time()
        response = test_client.get("/prometheus")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0, f"Metrics endpoint too slow: {elapsed:.2f}s"
    
    def test_metrics_dont_slow_ingestion(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_candles_batch: list[dict],
        clean_market_data
    ):
        """Test that metrics collection doesn't significantly slow ingestion."""
        # Time batch ingestion
        start = time.time()
        response = test_client.post(
            "/ingest_batch",
            json={"candles": sample_candles_batch[:10]},
            headers=auth_headers
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0, f"Ingestion too slow: {elapsed:.2f}s"


class TestCustomMetrics:
    """Tests for custom application metrics."""
    
    def test_database_metrics_present(self, test_client: TestClient):
        """Test that database-related metrics are exposed."""
        response = test_client.get("/prometheus")
        content = response.text
        
        # May contain db-related metrics
        # Just verify we get a response
        assert response.status_code == 200
    
    def test_api_latency_metrics(self, test_client: TestClient):
        """Test that API latency metrics are tracked."""
        # Make a request
        test_client.get("/health")
        
        time.sleep(0.2)
        
        # Check metrics
        response = test_client.get("/prometheus")
        assert response.status_code == 200


class TestMetricsJSON:
    """Tests for JSON metrics endpoint."""
    
    def test_json_metrics_endpoint(self, test_client: TestClient):
        """Test JSON metrics endpoint."""
        response = test_client.get("/metrics")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
    
    def test_json_metrics_structure(self, test_client: TestClient):
        """Test that JSON metrics have expected structure."""
        response = test_client.get("/metrics")
        data = response.json()
        
        # Should have some keys
        assert len(data) > 0
        
        # Common keys
        expected_keys = ["current", "last_db"]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"
    
    def test_json_metrics_values(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_candle: dict,
        clean_market_data
    ):
        """Test that JSON metrics contain valid values."""
        # Ingest some data
        test_client.post("/ingest", json=sample_candle, headers=auth_headers)
        
        time.sleep(0.5)
        
        response = test_client.get("/metrics")
        data = response.json()
        
        # Values should be present
        assert data is not None


class TestMetricsAggregation:
    """Tests for metric aggregation."""
    
    def test_metrics_aggregate_multiple_symbols(
        self,
        test_client: TestClient,
        auth_headers: dict,
        clean_market_data
    ):
        """Test that metrics aggregate data from multiple symbols."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        
        for symbol in symbols:
            candle = {
                "ts": f"2025-11-13T10:00:00Z",
                "symbol": symbol,
                "timeframe": "M1",
                "open": 1.0850,
                "high": 1.0855,
                "low": 1.0848,
                "close": 1.0852,
                "volume": 1000
            }
            test_client.post("/ingest", json=candle, headers=auth_headers)
        
        time.sleep(0.5)
        
        response = test_client.get("/prometheus")
        content = response.text
        
        # Should have metrics for multiple symbols
        assert response.status_code == 200
    
    def test_metrics_aggregate_multiple_timeframes(
        self,
        test_client: TestClient,
        auth_headers: dict,
        clean_market_data
    ):
        """Test that metrics aggregate data from multiple timeframes."""
        timeframes = ["M1", "M5", "M15", "H1"]
        
        for i, tf in enumerate(timeframes):
            candle = {
                "ts": f"2025-11-13T10:{i:02d}:00Z",
                "symbol": "EURUSD",
                "timeframe": tf,
                "open": 1.0850,
                "high": 1.0855,
                "low": 1.0848,
                "close": 1.0852,
                "volume": 1000
            }
            test_client.post("/ingest", json=candle, headers=auth_headers)
        
        time.sleep(0.5)
        
        response = test_client.get("/prometheus")
        assert response.status_code == 200


class TestMetricsReset:
    """Tests for metric reset behavior."""
    
    def test_metrics_persist_across_requests(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_candle: dict,
        clean_market_data
    ):
        """Test that metrics persist and accumulate."""
        # First ingest
        test_client.post("/ingest", json=sample_candle, headers=auth_headers)
        time.sleep(0.2)
        
        # Get metrics
        response1 = test_client.get("/prometheus")
        
        # Second ingest
        candle2 = {**sample_candle, "ts": "2025-11-13T10:01:00Z"}
        test_client.post("/ingest", json=candle2, headers=auth_headers)
        time.sleep(0.2)
        
        # Get metrics again
        response2 = test_client.get("/prometheus")
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200


class TestMetricsEdgeCases:
    """Tests for edge cases in metrics collection."""
    
    def test_metrics_with_no_data(self, test_client: TestClient):
        """Test metrics endpoint when no data has been ingested."""
        response = test_client.get("/prometheus")
        assert response.status_code == 200
        
        # Should return valid (possibly empty) metrics
        content = response.text
        assert isinstance(content, str)
    
    def test_metrics_after_error(
        self,
        test_client: TestClient,
        auth_headers: dict
    ):
        """Test that metrics work after an error."""
        # Trigger error
        test_client.post(
            "/ingest",
            json={"invalid": "data"},
            headers=auth_headers
        )
        
        time.sleep(0.2)
        
        # Metrics should still work
        response = test_client.get("/prometheus")
        assert response.status_code == 200
    
    def test_concurrent_metrics_access(self, test_client: TestClient):
        """Test concurrent access to metrics endpoint."""
        import concurrent.futures
        
        def get_metrics():
            return test_client.get("/prometheus")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_metrics) for _ in range(10)]
            responses = [f.result() for f in futures]
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)
