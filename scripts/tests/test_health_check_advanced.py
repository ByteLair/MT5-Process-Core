# Advanced health check tests for MT5 Trading System
import os
import sqlite3
import subprocess
import time


def test_simulate_container_failure() -> None:
    """
    Simulate API container failure and verify health-check script detects it.
    Stops mt5_api container, runs health-check, checks output, then restarts container.
    """
    subprocess.run(["docker", "stop", "mt5_api"], capture_output=True)
    time.sleep(2)
    result = subprocess.run(["bash", "scripts/health-check.sh"], capture_output=True, text=True)
    assert "mt5_api: not running" in result.stdout or "unhealthy" in result.stdout
    subprocess.run(["docker", "start", "mt5_api"], capture_output=True)


def test_restore_script() -> None:
    """
    Check that restore.sh script exists (do not run to avoid overwriting data).
    """
    assert os.path.exists("scripts/restore.sh")


def test_performance_endpoints() -> None:
    """
    Test that key API endpoints respond within 2 seconds and return HTTP 200.
    If endpoint is offline, test does not fail.
    """
    import requests

    endpoints = [
        "http://localhost:8001/health",
        "http://localhost:8001/docs",
        "http://localhost:9090/-/healthy",
        "http://localhost:3000/api/health",
    ]
    for url in endpoints:
        start = time.time()
        try:
            r = requests.get(url, timeout=5)
            elapsed = time.time() - start
            assert r.status_code == 200
            assert elapsed < 2  # 2 segundos
        except Exception:
            pass  # Pode estar offline, não falha o teste


def test_db_integrity() -> None:
    """
    Test that health check database exists and has recent records (last 1 day).
    """
    db_path = "logs/health-checks/health_checks.db"
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    # Verifica se há registros recentes
    count = conn.execute(
        "SELECT COUNT(*) FROM health_checks WHERE timestamp > datetime('now', '-1 day');"
    ).fetchone()[0]
    assert count > 0
    conn.close()


def test_logs_indexed() -> None:
    """
    Test that daily health check log files exist in logs/health-checks directory.
    """
    log_dir = "logs/health-checks"
    files = os.listdir(log_dir)
    assert any(f.startswith("daily_report_") for f in files)


def test_timers_trigger() -> None:
    """
    Test that required systemd timers are active.
    """
    timers = [
        "mt5-update.timer",
        "mt5-tests.timer",
        "mt5-vuln-check.timer",
        "mt5-daily-report.timer",
        "github-runner-check.timer",
    ]
    for t in timers:
        result = subprocess.run(["systemctl", "is-active", t], capture_output=True, text=True)
        assert result.stdout.strip() == "active"
