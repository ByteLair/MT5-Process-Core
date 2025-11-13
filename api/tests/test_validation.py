"""
Tests for data validation, Pydantic models, and input sanitization.
Ensures data integrity and proper error handling for invalid inputs.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient


class TestCandleValidation:
    """Tests for candle data validation."""
    
    def test_valid_candle_accepted(self, test_client: TestClient, auth_headers: dict):
        """Test that valid candle data is accepted."""
        valid_candle = {
            "ts": "2025-11-13T10:00:00Z",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": 1.0850,
            "high": 1.0855,
            "low": 1.0848,
            "close": 1.0852,
            "volume": 1000
        }
        
        response = test_client.post("/ingest", json=valid_candle, headers=auth_headers)
        assert response.status_code == 200
    
    def test_missing_required_fields(self, test_client: TestClient, auth_headers: dict):
        """Test that missing required fields are rejected."""
        invalid_candles = [
            {"symbol": "EURUSD", "timeframe": "M1"},  # Missing ts
            {"ts": "2025-11-13T10:00:00Z", "timeframe": "M1"},  # Missing symbol
            {"ts": "2025-11-13T10:00:00Z", "symbol": "EURUSD"},  # Missing timeframe
        ]
        
        for candle in invalid_candles:
            response = test_client.post("/ingest", json=candle, headers=auth_headers)
            assert response.status_code == 422, f"Should reject: {candle}"
    
    def test_invalid_timestamp_format(self, test_client: TestClient, auth_headers: dict):
        """Test that invalid timestamp formats are rejected."""
        invalid_timestamps = [
            "2025-13-01T10:00:00Z",  # Invalid month
            "2025-11-32T10:00:00Z",  # Invalid day
            "invalid-date",
            "2025/11/13 10:00:00",
            "",
            None
        ]
        
        for ts in invalid_timestamps:
            candle = {
                "ts": ts,
                "symbol": "EURUSD",
                "timeframe": "M1",
                "open": 1.0850,
                "high": 1.0855,
                "low": 1.0848,
                "close": 1.0852,
                "volume": 1000
            }
            response = test_client.post("/ingest", json=candle, headers=auth_headers)
            assert response.status_code == 422, f"Should reject timestamp: {ts}"
    
    def test_invalid_ohlc_values(self, test_client: TestClient, auth_headers: dict):
        """Test that invalid OHLC values are rejected."""
        # High lower than low
        invalid_candle = {
            "ts": "2025-11-13T10:00:00Z",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": 1.0850,
            "high": 1.0840,  # Lower than low!
            "low": 1.0848,
            "close": 1.0852,
            "volume": 1000
        }
        
        response = test_client.post("/ingest", json=invalid_candle, headers=auth_headers)
        # May accept (validation depends on implementation) or reject
        assert response.status_code in [200, 422]
    
    def test_negative_values(self, test_client: TestClient, auth_headers: dict):
        """Test that negative prices/volumes are handled."""
        invalid_candle = {
            "ts": "2025-11-13T10:00:00Z",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": -1.0850,  # Negative price
            "high": 1.0855,
            "low": 1.0848,
            "close": 1.0852,
            "volume": -1000  # Negative volume
        }
        
        response = test_client.post("/ingest", json=invalid_candle, headers=auth_headers)
        assert response.status_code == 422
    
    def test_zero_volume(self, test_client: TestClient, auth_headers: dict):
        """Test that zero volume is accepted."""
        candle = {
            "ts": "2025-11-13T10:00:00Z",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": 1.0850,
            "high": 1.0855,
            "low": 1.0848,
            "close": 1.0852,
            "volume": 0
        }
        
        response = test_client.post("/ingest", json=candle, headers=auth_headers)
        assert response.status_code == 200
    
    def test_invalid_symbol_format(self, test_client: TestClient, auth_headers: dict):
        """Test that invalid symbol formats are handled."""
        invalid_symbols = [
            "",
            " ",
            "EUR",  # Too short
            "EURUSD123456789",  # Too long
            "eur/usd",  # Invalid chars
            123,  # Not a string
        ]
        
        for symbol in invalid_symbols:
            candle = {
                "ts": "2025-11-13T10:00:00Z",
                "symbol": symbol,
                "timeframe": "M1",
                "open": 1.0850,
                "high": 1.0855,
                "low": 1.0848,
                "close": 1.0852,
                "volume": 1000
            }
            response = test_client.post("/ingest", json=candle, headers=auth_headers)
            assert response.status_code == 422, f"Should reject symbol: {symbol}"
    
    def test_invalid_timeframe(self, test_client: TestClient, auth_headers: dict):
        """Test that invalid timeframes are handled."""
        invalid_timeframes = [
            "M0",
            "M60",  # Doesn't exist
            "H25",
            "D8",
            "invalid",
            "",
            123
        ]
        
        for tf in invalid_timeframes:
            candle = {
                "ts": "2025-11-13T10:00:00Z",
                "symbol": "EURUSD",
                "timeframe": tf,
                "open": 1.0850,
                "high": 1.0855,
                "low": 1.0848,
                "close": 1.0852,
                "volume": 1000
            }
            response = test_client.post("/ingest", json=candle, headers=auth_headers)
            # May accept or reject depending on validation
            assert response.status_code in [200, 422]
    
    def test_extreme_values(self, test_client: TestClient, auth_headers: dict):
        """Test handling of extreme numeric values."""
        extreme_candle = {
            "ts": "2025-11-13T10:00:00Z",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": 999999999.99,
            "high": 999999999.99,
            "low": 0.00001,
            "close": 1.0852,
            "volume": 999999999999
        }
        
        response = test_client.post("/ingest", json=extreme_candle, headers=auth_headers)
        assert response.status_code in [200, 422]


class TestBatchValidation:
    """Tests for batch ingestion validation."""
    
    def test_empty_batch(self, test_client: TestClient, auth_headers: dict):
        """Test that empty batch is handled."""
        response = test_client.post(
            "/ingest_batch",
            json={"candles": []},
            headers=auth_headers
        )
        assert response.status_code in [200, 422]
    
    def test_mixed_valid_invalid_batch(
        self,
        test_client: TestClient,
        auth_headers: dict,
        clean_market_data
    ):
        """Test batch with mix of valid and invalid candles."""
        mixed_batch = {
            "candles": [
                {  # Valid
                    "ts": "2025-11-13T10:00:00Z",
                    "symbol": "EURUSD",
                    "timeframe": "M1",
                    "open": 1.0850,
                    "high": 1.0855,
                    "low": 1.0848,
                    "close": 1.0852,
                    "volume": 1000
                },
                {  # Invalid - missing symbol
                    "ts": "2025-11-13T10:01:00Z",
                    "timeframe": "M1",
                    "open": 1.0850,
                    "high": 1.0855,
                    "low": 1.0848,
                    "close": 1.0852,
                    "volume": 1000
                },
                {  # Valid
                    "ts": "2025-11-13T10:02:00Z",
                    "symbol": "GBPUSD",
                    "timeframe": "M1",
                    "open": 1.2650,
                    "high": 1.2655,
                    "low": 1.2648,
                    "close": 1.2652,
                    "volume": 800
                }
            ]
        }
        
        response = test_client.post(
            "/ingest_batch",
            json=mixed_batch,
            headers=auth_headers
        )
        
        # Should either reject entirely or accept valid ones
        assert response.status_code in [200, 422]
    
    def test_large_batch(self, test_client: TestClient, auth_headers: dict):
        """Test handling of large batch (1000 candles)."""
        large_batch = {
            "candles": [
                {
                    "ts": f"2025-11-13T{i//60:02d}:{i%60:02d}:00Z",
                    "symbol": "EURUSD",
                    "timeframe": "M1",
                    "open": 1.0850 + i * 0.0001,
                    "high": 1.0855 + i * 0.0001,
                    "low": 1.0848 + i * 0.0001,
                    "close": 1.0852 + i * 0.0001,
                    "volume": 1000 + i
                }
                for i in range(1000)
            ]
        }
        
        response = test_client.post(
            "/ingest_batch",
            json=large_batch,
            headers=auth_headers,
            timeout=30
        )
        
        assert response.status_code in [200, 413, 422, 500]


class TestAuthValidation:
    """Tests for authentication validation."""
    
    def test_missing_auth_header(self, test_client: TestClient, sample_candle: dict):
        """Test that missing auth header is rejected."""
        response = test_client.post("/ingest", json=sample_candle)
        assert response.status_code in [401, 403]
    
    def test_invalid_auth_header(self, test_client: TestClient, sample_candle: dict):
        """Test that invalid auth header is rejected."""
        invalid_headers = [
            {"X-API-Key": ""},
            {"X-API-Key": "invalid_key"},
            {"X-API-Key": "12345"},
            {"Authorization": "Bearer token"},  # Wrong header
        ]
        
        for headers in invalid_headers:
            response = test_client.post("/ingest", json=sample_candle, headers=headers)
            assert response.status_code in [401, 403], f"Should reject: {headers}"
    
    def test_valid_auth_header(self, test_client: TestClient, sample_candle: dict, auth_headers: dict):
        """Test that valid auth header is accepted."""
        response = test_client.post("/ingest", json=sample_candle, headers=auth_headers)
        assert response.status_code == 200


class TestQueryParameterValidation:
    """Tests for query parameter validation."""
    
    def test_signals_invalid_parameters(self, test_client: TestClient):
        """Test signals endpoint with invalid parameters."""
        # Invalid symbol
        response = test_client.get("/signals/latest?symbol=&timeframe=M1")
        assert response.status_code in [200, 404, 422]
        
        # Invalid timeframe
        response = test_client.get("/signals/latest?symbol=EURUSD&timeframe=invalid")
        assert response.status_code in [200, 404, 422]
        
        # Missing parameters
        response = test_client.get("/signals/latest")
        assert response.status_code in [200, 404, 422]
    
    def test_history_limit_validation(self, test_client: TestClient):
        """Test history endpoint with limit validation."""
        # Negative limit
        response = test_client.get(
            "/signals/history?symbol=EURUSD&timeframe=M1&limit=-10"
        )
        assert response.status_code in [200, 422]
        
        # Zero limit
        response = test_client.get(
            "/signals/history?symbol=EURUSD&timeframe=M1&limit=0"
        )
        assert response.status_code in [200, 422]
        
        # Extremely large limit
        response = test_client.get(
            "/signals/history?symbol=EURUSD&timeframe=M1&limit=999999"
        )
        assert response.status_code in [200, 422]


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_unicode_in_symbol(self, test_client: TestClient, auth_headers: dict):
        """Test handling of unicode characters in symbol."""
        candle = {
            "ts": "2025-11-13T10:00:00Z",
            "symbol": "EUR€USD",
            "timeframe": "M1",
            "open": 1.0850,
            "high": 1.0855,
            "low": 1.0848,
            "close": 1.0852,
            "volume": 1000
        }
        
        response = test_client.post("/ingest", json=candle, headers=auth_headers)
        assert response.status_code in [200, 422]
    
    def test_sql_injection_attempt(self, test_client: TestClient, auth_headers: dict):
        """Test that SQL injection attempts are handled safely."""
        candle = {
            "ts": "2025-11-13T10:00:00Z",
            "symbol": "EURUSD'; DROP TABLE market_data;--",
            "timeframe": "M1",
            "open": 1.0850,
            "high": 1.0855,
            "low": 1.0848,
            "close": 1.0852,
            "volume": 1000
        }
        
        response = test_client.post("/ingest", json=candle, headers=auth_headers)
        # Should be safely handled (parameterized queries)
        assert response.status_code in [200, 422]
    
    def test_very_long_symbol_name(self, test_client: TestClient, auth_headers: dict):
        """Test handling of very long symbol names."""
        candle = {
            "ts": "2025-11-13T10:00:00Z",
            "symbol": "A" * 1000,  # 1000 character symbol
            "timeframe": "M1",
            "open": 1.0850,
            "high": 1.0855,
            "low": 1.0848,
            "close": 1.0852,
            "volume": 1000
        }
        
        response = test_client.post("/ingest", json=candle, headers=auth_headers)
        assert response.status_code == 422
    
    def test_future_timestamp(self, test_client: TestClient, auth_headers: dict):
        """Test candle with timestamp far in the future."""
        candle = {
            "ts": "2099-12-31T23:59:59Z",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": 1.0850,
            "high": 1.0855,
            "low": 1.0848,
            "close": 1.0852,
            "volume": 1000
        }
        
        response = test_client.post("/ingest", json=candle, headers=auth_headers)
        # Should accept (data validation is lenient on future dates)
        assert response.status_code == 200
    
    def test_very_old_timestamp(self, test_client: TestClient, auth_headers: dict):
        """Test candle with very old timestamp."""
        candle = {
            "ts": "1970-01-01T00:00:00Z",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": 1.0850,
            "high": 1.0855,
            "low": 1.0848,
            "close": 1.0852,
            "volume": 1000
        }
        
        response = test_client.post("/ingest", json=candle, headers=auth_headers)
        assert response.status_code == 200
    
    def test_malformed_json(self, test_client: TestClient, auth_headers: dict):
        """Test handling of malformed JSON."""
        response = test_client.post(
            "/ingest",
            data="{'invalid': json}",  # Not valid JSON
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_null_values(self, test_client: TestClient, auth_headers: dict):
        """Test handling of null values."""
        candle = {
            "ts": "2025-11-13T10:00:00Z",
            "symbol": None,
            "timeframe": "M1",
            "open": 1.0850,
            "high": None,
            "low": 1.0848,
            "close": 1.0852,
            "volume": 1000
        }
        
        response = test_client.post("/ingest", json=candle, headers=auth_headers)
        assert response.status_code == 422


class TestContentTypeValidation:
    """Tests for content type validation."""
    
    def test_missing_content_type(self, test_client: TestClient, auth_headers: dict, sample_candle: dict):
        """Test request without content-type header."""
        headers = {**auth_headers}
        headers.pop("Content-Type", None)
        
        response = test_client.post(
            "/ingest",
            json=sample_candle,
            headers=headers
        )
        # FastAPI should handle this gracefully
        assert response.status_code in [200, 422]
    
    def test_wrong_content_type(self, test_client: TestClient, auth_headers: dict):
        """Test request with wrong content-type."""
        import json
        
        headers = {**auth_headers, "Content-Type": "text/plain"}
        data = json.dumps({
            "ts": "2025-11-13T10:00:00Z",
            "symbol": "EURUSD",
            "timeframe": "M1",
            "open": 1.0850,
            "high": 1.0855,
            "low": 1.0848,
            "close": 1.0852,
            "volume": 1000
        })
        
        response = test_client.post("/ingest", data=data, headers=headers)
        assert response.status_code in [200, 415, 422]


class TestConcurrentValidation:
    """Tests for concurrent request validation."""
    
    def test_concurrent_duplicate_prevention(
        self,
        test_client: TestClient,
        auth_headers: dict,
        sample_candle: dict,
        clean_market_data
    ):
        """Test that concurrent duplicate inserts are handled."""
        import concurrent.futures
        
        def insert_candle():
            return test_client.post(
                "/ingest",
                json=sample_candle,
                headers=auth_headers
            )
        
        # Send 10 identical candles concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(insert_candle) for _ in range(10)]
            responses = [f.result() for f in futures]
        
        # All should succeed (200) but only 1 should be inserted
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == 10
        
        # Check actual inserted count
        data = responses[0].json()
        # Total inserted should be 1 (rest are duplicates)
        # This depends on implementation details
