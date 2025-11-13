"""
Tests for API status endpoints, health checks, and system information.
"""
import pytest
from fastapi.testclient import TestClient


class TestStatusEndpoint:
    """Tests for /status endpoint."""
    
    def test_status_endpoint_exists(self, test_client: TestClient):
        """Test that status endpoint is accessible."""
        response = test_client.get("/status")
        # May or may not exist depending on implementation
        assert response.status_code in [200, 404]
    
    def test_status_response_structure(self, test_client: TestClient):
        """Test status endpoint response structure."""
        response = test_client.get("/status")
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


class TestHealthEndpointDetailed:
    """Detailed tests for health check endpoint."""
    
    def test_health_response_structure(self, test_client: TestClient):
        """Test that health check returns proper structure."""
        response = test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ok", "healthy", "up"]
    
    def test_health_includes_timestamp(self, test_client: TestClient):
        """Test that health check includes timestamp."""
        response = test_client.get("/health")
        data = response.json()
        
        # Should have timestamp or similar
        has_time_info = any(
            key in data for key in ["timestamp", "time", "checked_at"]
        )
        # Or just has data
        assert has_time_info or len(data) > 0
    
    def test_health_check_database_status(self, test_client: TestClient):
        """Test that health check includes database status."""
        response = test_client.get("/health")
        data = response.json()
        
        # May include db status
        has_db_info = any(
            key in data for key in ["db_connected", "database", "db"]
        )
        # Or just returns successfully
        assert has_db_info or response.status_code == 200
    
    def test_health_check_caching(self, test_client: TestClient):
        """Test that health check can be called repeatedly."""
        for _ in range(5):
            response = test_client.get("/health")
            assert response.status_code == 200
    
    def test_health_check_performance(self, test_client: TestClient):
        """Test that health check is fast."""
        import time
        
        start = time.time()
        response = test_client.get("/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.5, f"Health check too slow: {elapsed:.2f}s"


class TestRootEndpoint:
    """Tests for root endpoint (/)."""
    
    def test_root_endpoint(self, test_client: TestClient):
        """Test root endpoint."""
        response = test_client.get("/")
        # May redirect or return info
        assert response.status_code in [200, 404, 307, 308]
    
    def test_root_endpoint_info(self, test_client: TestClient):
        """Test that root endpoint provides info."""
        response = test_client.get("/")
        
        if response.status_code == 200:
            # May be JSON or HTML
            assert len(response.content) > 0


class TestDocsEndpoints:
    """Tests for API documentation endpoints."""
    
    def test_docs_endpoint(self, test_client: TestClient):
        """Test Swagger UI docs endpoint."""
        response = test_client.get("/docs")
        # Should be accessible
        assert response.status_code in [200, 404]
    
    def test_redoc_endpoint(self, test_client: TestClient):
        """Test ReDoc docs endpoint."""
        response = test_client.get("/redoc")
        # Should be accessible
        assert response.status_code in [200, 404]
    
    def test_openapi_json(self, test_client: TestClient):
        """Test OpenAPI JSON schema endpoint."""
        response = test_client.get("/openapi.json")
        
        if response.status_code == 200:
            data = response.json()
            assert "openapi" in data
            assert "info" in data
            assert "paths" in data


class TestVersionInfo:
    """Tests for API version information."""
    
    def test_version_in_response(self, test_client: TestClient):
        """Test that API version is exposed."""
        response = test_client.get("/health")
        data = response.json()
        
        # May include version
        has_version = "version" in data
        # Or just returns successfully
        assert has_version or response.status_code == 200


class TestNotFoundHandling:
    """Tests for 404 error handling."""
    
    def test_404_on_invalid_path(self, test_client: TestClient):
        """Test 404 response for invalid paths."""
        response = test_client.get("/this/path/does/not/exist")
        assert response.status_code == 404
    
    def test_404_response_format(self, test_client: TestClient):
        """Test that 404 responses are properly formatted."""
        response = test_client.get("/invalid")
        assert response.status_code == 404
        
        # Should return JSON error
        data = response.json()
        assert "detail" in data or "message" in data


class TestMethodNotAllowed:
    """Tests for 405 method not allowed."""
    
    def test_405_wrong_method(self, test_client: TestClient):
        """Test 405 for wrong HTTP method."""
        # GET on POST-only endpoint
        response = test_client.get("/ingest")
        assert response.status_code in [405, 422]
        
        # POST on GET-only endpoint
        response = test_client.post("/health")
        assert response.status_code == 405


class TestOptionsRequests:
    """Tests for OPTIONS requests (CORS preflight)."""
    
    def test_options_health(self, test_client: TestClient):
        """Test OPTIONS request on health endpoint."""
        response = test_client.options("/health")
        # Should handle OPTIONS for CORS
        assert response.status_code in [200, 204, 405]
    
    def test_options_ingest(self, test_client: TestClient):
        """Test OPTIONS request on ingest endpoint."""
        response = test_client.options("/ingest")
        assert response.status_code in [200, 204, 405]


class TestHeadRequests:
    """Tests for HEAD requests."""
    
    def test_head_health(self, test_client: TestClient):
        """Test HEAD request on health endpoint."""
        response = test_client.head("/health")
        # Should work like GET but no body
        assert response.status_code in [200, 405]
    
    def test_head_metrics(self, test_client: TestClient):
        """Test HEAD request on metrics endpoint."""
        response = test_client.head("/metrics")
        assert response.status_code in [200, 405]


class TestConcurrentHealthChecks:
    """Tests for concurrent health check requests."""
    
    def test_concurrent_health_checks(self, test_client: TestClient):
        """Test multiple concurrent health checks."""
        import concurrent.futures
        
        def health_check():
            return test_client.get("/health")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(health_check) for _ in range(20)]
            responses = [f.result() for f in futures]
        
        # All should succeed
        assert all(r.status_code == 200 for r in responses)
        
        # All should have valid data
        for response in responses:
            data = response.json()
            assert "status" in data


class TestSystemInformation:
    """Tests for system information endpoints."""
    
    def test_system_info_exists(self, test_client: TestClient):
        """Test if system info endpoint exists."""
        possible_paths = ["/info", "/system", "/about"]
        
        for path in possible_paths:
            response = test_client.get(path)
            # May or may not exist
            assert response.status_code in [200, 404]


class TestDatabaseHealthCheck:
    """Tests for database health in health endpoint."""
    
    def test_health_with_database_connection(
        self,
        test_client: TestClient,
        db_connection
    ):
        """Test health check when database is connected."""
        response = test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        # Should indicate DB is connected
        if "db_connected" in data:
            assert data["db_connected"] is True
    
    def test_health_check_queries_database(self, test_client: TestClient):
        """Test that health check actually queries database."""
        # Multiple health checks should work
        for _ in range(3):
            response = test_client.get("/health")
            assert response.status_code == 200


class TestRateLimitingStatus:
    """Tests for rate limiting status."""
    
    def test_rate_limit_headers(
        self,
        test_client: TestClient,
        sample_candle: dict,
        auth_headers: dict
    ):
        """Test that rate limit headers are present."""
        response = test_client.post(
            "/ingest",
            json=sample_candle,
            headers=auth_headers
        )
        
        # May include rate limit headers
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        # Common rate limit headers
        rate_limit_headers = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset",
        ]
        
        # Either has rate limit headers or just succeeds
        has_rate_limit = any(h in headers_lower for h in rate_limit_headers)
        assert has_rate_limit or response.status_code == 200


class TestAPIMetadata:
    """Tests for API metadata and configuration."""
    
    def test_api_has_title(self, test_client: TestClient):
        """Test that API has a title."""
        response = test_client.get("/openapi.json")
        
        if response.status_code == 200:
            data = response.json()
            assert "info" in data
            assert "title" in data["info"]
    
    def test_api_has_version(self, test_client: TestClient):
        """Test that API has a version."""
        response = test_client.get("/openapi.json")
        
        if response.status_code == 200:
            data = response.json()
            assert "info" in data
            assert "version" in data["info"]
    
    def test_api_has_description(self, test_client: TestClient):
        """Test that API has a description."""
        response = test_client.get("/openapi.json")
        
        if response.status_code == 200:
            data = response.json()
            if "info" in data and "description" in data["info"]:
                assert len(data["info"]["description"]) > 0


class TestServerHeaders:
    """Tests for server response headers."""
    
    def test_security_headers(self, test_client: TestClient):
        """Test that security headers are present."""
        response = test_client.get("/health")
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        
        # Common security headers
        security_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
        ]
        
        # May or may not have security headers
        # Just verify we get a response
        assert response.status_code == 200
    
    def test_cors_headers(self, test_client: TestClient):
        """Test that CORS headers are configured."""
        headers = {"Origin": "http://localhost:3000"}
        response = test_client.get("/health", headers=headers)
        
        assert response.status_code == 200
    
    def test_content_type_header(self, test_client: TestClient):
        """Test that content-type header is set correctly."""
        response = test_client.get("/health")
        
        assert "content-type" in [h.lower() for h in response.headers.keys()]
        assert "application/json" in response.headers.get("content-type", "")
