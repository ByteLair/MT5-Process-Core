import pytest
from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_latest_signal():
    response = client.get("/signals/latest?symbol=EURUSD&period=M1")
    assert response.status_code == 200
    data = response.json()
    assert "signal_id" in data
    assert data["symbol"] == "EURUSD"
    assert data["timeframe"] == "M1"

def test_orders_feedback():
    payload = {
        "signal_id": "test-id",
        "order_id": 123,
        "status": "FILLED",
        "price": 1.2345,
        "slippage": 0.1,
        "message": "ok",
        "ts": "2025-10-18T10:00:00Z"
    }
    response = client.post("/orders/feedback", json=payload)
    assert response.status_code == 200
    assert response.json()["ok"] is True
