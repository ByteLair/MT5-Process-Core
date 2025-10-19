
# Test suite for health check script and database
import subprocess
import os
import sqlite3


def test_health_check_script_runs():
    """
    Test that the health-check.sh script runs successfully and outputs expected message.
    """
    result = subprocess.run(["bash", "scripts/health-check.sh"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Health check completed" in result.stdout


def test_health_check_db_exists():
    """
    Test that the health check database exists and has required tables.
    """
    db_path = "logs/health-checks/health_checks.db"
    assert os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    assert "health_checks" in tables
    assert "alerts" in tables
    conn.close()


def test_health_check_daily_report():
    """
    Test that the health-check.sh script generates a daily report with all expected sections.
    """
    result = subprocess.run(["bash", "scripts/health-check.sh", "--report"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "SUMMARY" in result.stdout
    assert "CONTAINER STATUS" in result.stdout
    assert "API ENDPOINTS" in result.stdout
    assert "DATABASE PERFORMANCE" in result.stdout
    assert "ALERTS" in result.stdout
    assert "RECENT FAILURES" in result.stdout


def test_health_check_alerts():
    """
    Test that unresolved alerts can be queried from the database without error.
    Does not require any alerts to exist, only that query works and returns a list.
    """
    db_path = "logs/health-checks/health_checks.db"
    conn = sqlite3.connect(db_path)
    alerts = conn.execute("SELECT * FROM alerts WHERE resolved=0;").fetchall()
    # Não exige alertas, mas garante consulta sem erro
    assert isinstance(alerts, list)
    conn.close()
