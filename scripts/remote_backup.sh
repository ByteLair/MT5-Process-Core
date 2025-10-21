#!/bin/bash
# scripts/remote_backup.sh
# Realiza backup do banco e arquivos essenciais para outro servidor

REMOTE_USER="felipe"
REMOTE_IP="100.113.13.126"
REMOTE_DIR="/home/felipe/mt5-backup/$(date +%Y-%m-%d)"
LOCAL_DB="mt5_trading"
LOCAL_DB_USER="trader"
LOCAL_DB_CONTAINER="mt5_db"
EMAIL="kuramopr@gmail.com"

echo "[INFO] Iniciando backup remoto em $(date)"

# Cria dump do banco
echo "[INFO] Criando dump do banco de dados..."
DUMP_FILE="/tmp/mt5_db_backup_$(date +%Y-%m-%d_%H-%M-%S).sql"
docker exec $LOCAL_DB_CONTAINER pg_dump -U $LOCAL_DB_USER $LOCAL_DB > "$DUMP_FILE"
DB_SIZE=$(du -h "$DUMP_FILE" | cut -f1)
echo "[OK] Dump criado: $DUMP_FILE ($DB_SIZE)"

# Backup de configurações do Grafana
echo "[INFO] Backup das configurações do Grafana..."
GRAFANA_FILE="/tmp/mt5_grafana_backup_$(date +%Y-%m-%d_%H-%M-%S).tar.gz"
tar czf "$GRAFANA_FILE" grafana/provisioning/

# Backup de configurações do Prometheus
echo "[INFO] Backup das configurações do Prometheus..."
PROMETHEUS_FILE="/tmp/mt5_prometheus_backup_$(date +%Y-%m-%d_%H-%M-%S).tar.gz"
tar czf "$PROMETHEUS_FILE" prometheus/

# Backup de configurações do Loki
echo "[INFO] Backup das configurações do Loki..."
LOKI_FILE="/tmp/mt5_loki_backup_$(date +%Y-%m-%d_%H-%M-%S).tar.gz"
tar czf "$LOKI_FILE" loki/

# Cria tar dos arquivos essenciais
echo "[INFO] Compactando arquivos essenciais..."
TAR_FILE="/tmp/mt5_files_backup_$(date +%Y-%m-%d_%H-%M-%S).tar.gz"
tar czf "$TAR_FILE" \
    data/ \
    ml/models/ \
    logs/ \
    scripts/ \
    api/requirements.txt \
    ml/requirements-ml.txt \
    docker-compose.yml \
    docker-compose.override.yml \
    systemd/ \
    README.md
FILES_SIZE=$(du -h "$TAR_FILE" | cut -f1)
echo "[OK] Arquivos compactados: $TAR_FILE ($FILES_SIZE)"

# Envia para o servidor remoto
echo "[INFO] Enviando backups para $REMOTE_IP..."
ssh $REMOTE_USER@$REMOTE_IP "mkdir -p $REMOTE_DIR"

scp "$DUMP_FILE" $REMOTE_USER@$REMOTE_IP:"$REMOTE_DIR/"
scp "$TAR_FILE" $REMOTE_USER@$REMOTE_IP:"$REMOTE_DIR/"
scp "$GRAFANA_FILE" $REMOTE_USER@$REMOTE_IP:"$REMOTE_DIR/"
scp "$PROMETHEUS_FILE" $REMOTE_USER@$REMOTE_IP:"$REMOTE_DIR/"
scp "$LOKI_FILE" $REMOTE_USER@$REMOTE_IP:"$REMOTE_DIR/"

# Verifica integridade no servidor remoto
echo "[INFO] Verificando integridade dos backups..."
REMOTE_FILES=$(ssh $REMOTE_USER@$REMOTE_IP "ls -lh $REMOTE_DIR")

# Limpa arquivos temporários
rm -f "$DUMP_FILE" "$TAR_FILE" "$GRAFANA_FILE" "$PROMETHEUS_FILE" "$LOKI_FILE"

# Envia relatório por email
REPORT="Backup remoto MT5 concluído em $(date)

Servidor destino: $REMOTE_IP:$REMOTE_DIR

Arquivos enviados:
- Banco de dados: $DB_SIZE
- Arquivos essenciais: $FILES_SIZE
- Grafana, Prometheus, Loki: configurações completas

Arquivos no servidor remoto:
$REMOTE_FILES
"

echo "$REPORT" | mailx -s "[MT5] Backup remoto concluído" "$EMAIL"
echo "[OK] Backup enviado para $REMOTE_IP:$REMOTE_DIR e relatório enviado por email"
