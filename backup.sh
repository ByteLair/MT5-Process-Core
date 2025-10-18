#!/bin/bash
set -e

# MT5 Trading - Automated Backup Script
# Faz backup do banco de dados, modelos ML e configurações

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="mt5_backup_${TIMESTAMP}"
RETENTION_DAYS=${RETENTION_DAYS:-7}

echo "=========================================="
echo "💾 MT5 Trading - Automated Backup"
echo "=========================================="
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

echo -e "${BLUE}📦 Backup Directory: $BACKUP_DIR/$BACKUP_NAME${NC}"
echo ""

# 1. Backup PostgreSQL Database
echo -e "${BLUE}🗄️  Backing up PostgreSQL database...${NC}"
if docker exec mt5_db pg_dump -U trader -d mt5_trading > "$BACKUP_DIR/$BACKUP_NAME/database.sql" 2>/dev/null; then
    db_size=$(du -h "$BACKUP_DIR/$BACKUP_NAME/database.sql" | cut -f1)
    echo -e "${GREEN}✅ Database backup completed ($db_size)${NC}"
else
    echo -e "${RED}❌ Database backup failed${NC}"
    exit 1
fi

# 2. Backup ML Models
echo -e "${BLUE}🤖 Backing up ML models...${NC}"
mkdir -p "$BACKUP_DIR/$BACKUP_NAME/models"

if docker run --rm -v models_mt5:/models -v "$(pwd)/$BACKUP_DIR/$BACKUP_NAME/models":/backup alpine sh -c "cp -r /models/* /backup/ 2>/dev/null || true"; then
    model_count=$(find "$BACKUP_DIR/$BACKUP_NAME/models" -type f 2>/dev/null | wc -l)
    if [ "$model_count" -gt 0 ]; then
        echo -e "${GREEN}✅ ML models backup completed ($model_count files)${NC}"
    else
        echo -e "${YELLOW}⚠️  No ML models found${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  ML models backup skipped${NC}"
fi

# 3. Backup Configuration Files
echo -e "${BLUE}⚙️  Backing up configuration files...${NC}"
mkdir -p "$BACKUP_DIR/$BACKUP_NAME/config"

# Copy configuration files
config_files=(
    ".env"
    "docker-compose.yml"
    "prometheus.yml"
    "grafana/provisioning"
)

for file in "${config_files[@]}"; do
    if [ -e "$file" ]; then
        if [ -d "$file" ]; then
            cp -r "$file" "$BACKUP_DIR/$BACKUP_NAME/config/"
        else
            cp "$file" "$BACKUP_DIR/$BACKUP_NAME/config/"
        fi
    fi
done

echo -e "${GREEN}✅ Configuration files backup completed${NC}"

# 4. Backup Grafana Data
echo -e "${BLUE}📊 Backing up Grafana data...${NC}"
mkdir -p "$BACKUP_DIR/$BACKUP_NAME/grafana"

if docker cp mt5_grafana:/var/lib/grafana "$BACKUP_DIR/$BACKUP_NAME/grafana/" 2>/dev/null; then
    echo -e "${GREEN}✅ Grafana data backup completed${NC}"
else
    echo -e "${YELLOW}⚠️  Grafana backup skipped${NC}"
fi

# 5. Create Backup Metadata
echo -e "${BLUE}📝 Creating backup metadata...${NC}"
cat > "$BACKUP_DIR/$BACKUP_NAME/metadata.txt" << EOF
MT5 Trading Backup
==================
Timestamp: $(date)
Hostname: $(hostname)
Backup Directory: $BACKUP_DIR/$BACKUP_NAME

Components:
- PostgreSQL Database: $([ -f "$BACKUP_DIR/$BACKUP_NAME/database.sql" ] && echo "✅" || echo "❌")
- ML Models: $([ -d "$BACKUP_DIR/$BACKUP_NAME/models" ] && echo "✅" || echo "❌")
- Configuration: $([ -d "$BACKUP_DIR/$BACKUP_NAME/config" ] && echo "✅" || echo "❌")
- Grafana Data: $([ -d "$BACKUP_DIR/$BACKUP_NAME/grafana" ] && echo "✅" || echo "❌")

Database Stats:
- Total Records: $(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT COUNT(*) FROM market_data;" 2>/dev/null | xargs || echo "N/A")
- Active Symbols: $(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT COUNT(DISTINCT symbol) FROM market_data;" 2>/dev/null | xargs || echo "N/A")
- Database Size: $(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT pg_size_pretty(pg_database_size('mt5_trading'));" 2>/dev/null | xargs || echo "N/A")
EOF

echo -e "${GREEN}✅ Metadata created${NC}"

# 6. Compress Backup
echo -e "${BLUE}🗜️  Compressing backup...${NC}"
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME" 2>/dev/null

if [ -f "${BACKUP_NAME}.tar.gz" ]; then
    backup_size=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
    echo -e "${GREEN}✅ Backup compressed ($backup_size)${NC}"
    
    # Remove uncompressed backup
    rm -rf "$BACKUP_NAME"
else
    echo -e "${RED}❌ Compression failed${NC}"
    cd - > /dev/null
    exit 1
fi

cd - > /dev/null

# 7. Clean Old Backups
echo -e "${BLUE}🧹 Cleaning old backups (retention: $RETENTION_DAYS days)...${NC}"
find "$BACKUP_DIR" -name "mt5_backup_*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

remaining_backups=$(find "$BACKUP_DIR" -name "mt5_backup_*.tar.gz" -type f | wc -l)
echo -e "${GREEN}✅ Cleanup completed ($remaining_backups backups remaining)${NC}"

# 8. Summary
echo ""
echo "=========================================="
echo -e "${GREEN}✅ Backup completed successfully!${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}Backup Location:${NC}"
echo "   $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo ""
echo -e "${BLUE}Backup Size:${NC}"
echo "   $(du -h "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" | cut -f1)"
echo ""
echo -e "${BLUE}Restore Instructions:${NC}"
echo "   1. Extract: tar -xzf ${BACKUP_NAME}.tar.gz"
echo "   2. Restore DB: docker exec -i mt5_db psql -U trader -d mt5_trading < ${BACKUP_NAME}/database.sql"
echo "   3. Restore models: docker cp ${BACKUP_NAME}/models/. mt5_ml_trainer:/models/"
echo "   4. Restore configs: cp -r ${BACKUP_NAME}/config/* ./"
echo ""
echo -e "${BLUE}Automation (Cron):${NC}"
echo "   Add to crontab: 0 2 * * * /path/to/backup.sh"
echo "   Daily at 2 AM with retention: 0 2 * * * RETENTION_DAYS=30 /path/to/backup.sh"
echo ""
