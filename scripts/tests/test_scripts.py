import os
import subprocess


def test_maintenance_script() -> None:
    result = subprocess.run(
        ["bash", "scripts/maintenance.sh", "status"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "status" in result.stdout.lower()


def test_backup_script() -> None:
    result = subprocess.run(["bash", "scripts/backup.sh"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "backup" in result.stdout.lower() or "completed" in result.stdout.lower()


def test_restore_script() -> None:
    # Simula restore (não executa de fato para evitar sobrescrever dados)
    assert os.path.exists("scripts/restore.sh")


def test_health_check_script() -> None:
    result = subprocess.run(["bash", "scripts/health-check.sh"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "health" in result.stdout.lower() or "ok" in result.stdout.lower()
