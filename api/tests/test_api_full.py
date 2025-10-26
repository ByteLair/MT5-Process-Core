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
        "ts": "2025-10-18T10:00:00Z",
    }
    response = client.post("/orders/feedback", json=payload)
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_signals():
    response = client.get("/signals?timeframe=M1")
    assert response.status_code in [200, 404]  # 404 se não houver dados
    if response.status_code == 200:
        assert isinstance(response.json(), list)


def test_signals_save():
    response = client.post("/signals/save?timeframe=M1")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert "saved" in response.json()


def test_signals_history():
    response = client.get("/signals/history?symbol=EURUSD&timeframe=M1&limit=10")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert isinstance(response.json(), list)


def test_signals_latest():
    response = client.get("/signals/latest?timeframe=M1")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert isinstance(response.json(), list)


def test_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "current" in data
    assert "last_db" in data
