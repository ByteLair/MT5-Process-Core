#!/usr/bin/env bash
################################################################################
# MT5 Trading DB - Automated Test Suite
################################################################################
set -euo pipefail

fail() { echo "[FAIL] $1"; exit 1; }
pass() { echo "[PASS] $1"; }

# 1. Testar execução dos scripts principais
sudo bash scripts/backup.sh || fail "backup.sh falhou"
sudo bash scripts/backup-full-repo.sh || fail "backup-full-repo.sh falhou"
sudo bash scripts/monitor-backup.sh || fail "monitor-backup.sh falhou"
sudo bash scripts/backup-metrics-exporter.sh || fail "backup-metrics-exporter.sh falhou"
pass "Execução dos scripts principais"

# 2. Verificar geração de arquivos
ls /var/backups/mt5/*.dump || fail "Arquivo de dump não gerado"
ls /var/backups/mt5/*.sha256 || fail "Arquivo de checksum não gerado"
ls /var/backups/mt5/logs/*.log || fail "Arquivo de log não gerado"
ls /var/backups/mt5/backup_metrics.prom || fail "Arquivo de métricas não gerado"
pass "Arquivos gerados corretamente"

# 3. Validar integridade do dump
cd /var/backups/mt5
sha256sum -c *.sha256 || fail "Integridade do dump falhou"
pass "Integridade do dump validada"


# 4. Testar API de backup (health)
if [ -f /etc/default/mt5-backup ]; then
	source /etc/default/mt5-backup
fi
curl -sS --max-time 5 "$BACKUP_API_URL/health" | grep 'ok' || fail "API health check falhou"
pass "API health check"

# 5. Testar upload remoto
sudo bash scripts/teste-backup-upload.sh || fail "Upload remoto falhou"
pass "Upload remoto testado"

# 6. Testar restore automatizado (simulado)
pg_restore --list /var/backups/mt5/*.dump || fail "pg_restore list falhou"
pass "pg_restore simulado"

# 7. Testar permissões
[ "$(id -u)" -eq 0 ] || fail "Script não está rodando como root"
pass "Permissões de root validadas"

# 8. Testar proteção de arquivos sensíveis
stat -c '%a' /etc/default/mt5-backup | grep -E '600|400' || fail "Permissão do arquivo de configuração insegura"
pass "Permissão do arquivo de configuração"

# 9. Testar exportação de métricas Prometheus
cat /var/backups/mt5/backup_metrics.prom | grep 'mt5_backup_status' || fail "Métricas Prometheus não exportadas"
pass "Exportação de métricas Prometheus"

# 10. Testar rotação de backups
ls /var/backups/mt5/*.dump | wc -l | grep -E '^[1-3]$' || fail "Rotação de backups não está correta"
pass "Rotação de backups validada"

echo "[ALL TESTS PASSED]"
exit 0
