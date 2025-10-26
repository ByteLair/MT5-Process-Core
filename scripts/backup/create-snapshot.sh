#!/bin/bash
################################################################################
# MT5 Trading - Repository Snapshot System
#
# Creates complete snapshots of the repository including:
# - Git repository (bundle)
# - Database backups
# - Volumes data
# - Configuration files
# - Logs (optional)
#
# Usage: ./create-snapshot.sh [options]
#   -f, --full          Include logs and temporary files
#   -r, --remote        Upload to remote storage
#   -n, --name NAME     Custom snapshot name
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_DIR="/home/felipe/MT5-Process-Core-full"
BACKUP_BASE_DIR="/home/felipe/backups/snapshots"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SNAPSHOT_NAME="mt5-snapshot-${TIMESTAMP}"
INCLUDE_LOGS=false
UPLOAD_REMOTE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--full)
            INCLUDE_LOGS=true
            shift
            ;;
        -r|--remote)
            UPLOAD_REMOTE=true
            shift
            ;;
        -n|--name)
            SNAPSHOT_NAME="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "  -f, --full       Include logs and temporary files"
            echo "  -r, --remote     Upload to remote storage"
            echo "  -n, --name NAME  Custom snapshot name"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

SNAPSHOT_DIR="${BACKUP_BASE_DIR}/${SNAPSHOT_NAME}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         MT5 Trading - Repository Snapshot Creator             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}📸 Snapshot: ${SNAPSHOT_NAME}${NC}"
echo -e "${GREEN}📁 Location: ${SNAPSHOT_DIR}${NC}"
echo ""

# Create snapshot directory
mkdir -p "${SNAPSHOT_DIR}"
cd "${REPO_DIR}"

################################################################################
# 1. Git Repository Bundle
################################################################################
echo -e "${BLUE}[1/7]${NC} Creating git repository bundle..."
git bundle create "${SNAPSHOT_DIR}/repository.bundle" --all
echo -e "${GREEN}✓${NC} Git bundle created"

################################################################################
# 2. Git Metadata
################################################################################
echo -e "${BLUE}[2/7]${NC} Saving git metadata..."
{
    echo "Snapshot Date: $(date)"
    echo "Current Branch: $(git branch --show-current)"
    echo "Last Commit: $(git log -1 --oneline)"
    echo "Git Status:"
    git status --short
    echo ""
    echo "Remotes:"
    git remote -v
    echo ""
    echo "Tags:"
    git tag -l
} > "${SNAPSHOT_DIR}/git-info.txt"
echo -e "${GREEN}✓${NC} Git metadata saved"

################################################################################
# 3. Database Backup
################################################################################
echo -e "${BLUE}[3/7]${NC} Creating database backup..."
if docker ps | grep -q mt5_db; then
    docker exec mt5_db pg_dumpall -U trader | gzip > "${SNAPSHOT_DIR}/database-full.sql.gz"

    # Individual databases
    docker exec mt5_db pg_dump -U trader mt5_trading | gzip > "${SNAPSHOT_DIR}/database-mt5_trading.sql.gz"

    # Database size info
    docker exec mt5_db psql -U trader -d mt5_trading -c "\
        SELECT
            pg_size_pretty(pg_database_size('mt5_trading')) as db_size,
            COUNT(*) as table_count
        FROM information_schema.tables
        WHERE table_schema = 'public';" > "${SNAPSHOT_DIR}/database-info.txt"

    echo -e "${GREEN}✓${NC} Database backup created"
else
    echo -e "${YELLOW}⚠${NC}  Database container not running, skipping DB backup"
fi

################################################################################
# 4. Docker Volumes
################################################################################
echo -e "${BLUE}[4/7]${NC} Backing up Docker volumes..."
VOLUME_BACKUP_DIR="${SNAPSHOT_DIR}/volumes"
mkdir -p "${VOLUME_BACKUP_DIR}"

# List of volumes to backup
VOLUMES=(
    "mt5-trading-db_db_data"
    "mt5-trading-db_prometheus_data"
    "mt5-trading-db_grafana_data"
    "mt5-trading-db_loki_data"
    "mt5-trading-db_jaeger_data"
    "models_mt5"
)

for volume in "${VOLUMES[@]}"; do
    if docker volume inspect "$volume" >/dev/null 2>&1; then
        echo -e "  Backing up ${volume}..."
        docker run --rm \
            -v "${volume}:/data:ro" \
            -v "${VOLUME_BACKUP_DIR}:/backup" \
            alpine \
            tar czf "/backup/${volume}.tar.gz" -C /data . 2>/dev/null || true
        echo -e "${GREEN}  ✓${NC} ${volume}"
    else
        echo -e "${YELLOW}  ⚠${NC}  Volume ${volume} not found"
    fi
done

################################################################################
# 5. Configuration Files
################################################################################
echo -e "${BLUE}[5/7]${NC} Copying configuration files..."
CONFIG_DIR="${SNAPSHOT_DIR}/config"
mkdir -p "${CONFIG_DIR}"

# Copy important configs
cp -r docker-compose*.yml "${CONFIG_DIR}/" 2>/dev/null || true
cp -r .env* "${CONFIG_DIR}/" 2>/dev/null || true
cp -r prometheus.yml "${CONFIG_DIR}/" 2>/dev/null || true
cp -r loki/ "${CONFIG_DIR}/" 2>/dev/null || true
cp -r grafana/provisioning/ "${CONFIG_DIR}/grafana-provisioning/" 2>/dev/null || true
cp -r k8s/ "${CONFIG_DIR}/" 2>/dev/null || true
cp -r nginx/ "${CONFIG_DIR}/" 2>/dev/null || true

# Create inventory of configs
find "${CONFIG_DIR}" -type f > "${SNAPSHOT_DIR}/config-inventory.txt"
echo -e "${GREEN}✓${NC} Configuration files copied"

################################################################################
# 6. Logs (Optional)
################################################################################
if [ "$INCLUDE_LOGS" = true ]; then
    echo -e "${BLUE}[6/7]${NC} Including logs in snapshot..."
    LOGS_DIR="${SNAPSHOT_DIR}/logs"
    mkdir -p "${LOGS_DIR}"

    # Copy recent logs only (last 7 days)
    find ./logs -type f -mtime -7 -exec cp --parents {} "${LOGS_DIR}/" \; 2>/dev/null || true

    # Docker logs
    mkdir -p "${LOGS_DIR}/docker"
    for container in $(docker ps --format "{{.Names}}" | grep mt5_); do
        docker logs --tail 1000 "$container" > "${LOGS_DIR}/docker/${container}.log" 2>&1 || true
    done

    echo -e "${GREEN}✓${NC} Logs included"
else
    echo -e "${BLUE}[6/7]${NC} Skipping logs (use --full to include)"
fi

################################################################################
# 7. Snapshot Metadata
################################################################################
echo -e "${BLUE}[7/7]${NC} Creating snapshot metadata..."
{
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║           MT5 Trading - Snapshot Metadata                     ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Snapshot Name: ${SNAPSHOT_NAME}"
    echo "Created: $(date)"
    echo "Hostname: $(hostname)"
    echo "User: $(whoami)"
    echo ""
    echo "--- System Info ---"
    echo "OS: $(uname -s) $(uname -r)"
    echo "Docker Version: $(docker --version)"
    echo "Docker Compose Version: $(docker-compose --version)"
    echo ""
    echo "--- Running Containers ---"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Size}}"
    echo ""
    echo "--- Docker Volumes ---"
    docker volume ls | grep mt5
    echo ""
    echo "--- Snapshot Contents ---"
    du -sh "${SNAPSHOT_DIR}"/*
    echo ""
    echo "--- Included Components ---"
    [ -f "${SNAPSHOT_DIR}/repository.bundle" ] && echo "✓ Git repository bundle"
    [ -f "${SNAPSHOT_DIR}/git-info.txt" ] && echo "✓ Git metadata"
    [ -f "${SNAPSHOT_DIR}/database-full.sql.gz" ] && echo "✓ Database backup (full)"
    [ -f "${SNAPSHOT_DIR}/database-mt5_trading.sql.gz" ] && echo "✓ Database backup (mt5_trading)"
    [ -d "${SNAPSHOT_DIR}/volumes" ] && echo "✓ Docker volumes ($(ls -1 ${SNAPSHOT_DIR}/volumes | wc -l) files)"
    [ -d "${SNAPSHOT_DIR}/config" ] && echo "✓ Configuration files"
    [ -d "${SNAPSHOT_DIR}/logs" ] && echo "✓ Logs" || echo "✗ Logs (not included)"
    echo ""
    echo "--- Restore Command ---"
    echo "To restore this snapshot, run:"
    echo "  ./scripts/backup/restore-snapshot.sh ${SNAPSHOT_NAME}"
    echo ""
} > "${SNAPSHOT_DIR}/SNAPSHOT_INFO.txt"

# Create checksum file
echo -e "${BLUE}Computing checksums...${NC}"
cd "${SNAPSHOT_DIR}"
find . -type f -exec sha256sum {} \; > checksums.sha256
cd "${REPO_DIR}"

echo -e "${GREEN}✓${NC} Snapshot metadata created"

################################################################################
# Compress Snapshot
################################################################################
echo ""
echo -e "${BLUE}Compressing snapshot...${NC}"
cd "${BACKUP_BASE_DIR}"
tar czf "${SNAPSHOT_NAME}.tar.gz" "${SNAPSHOT_NAME}/"
SNAPSHOT_SIZE=$(du -sh "${SNAPSHOT_NAME}.tar.gz" | cut -f1)
echo -e "${GREEN}✓${NC} Snapshot compressed: ${SNAPSHOT_SIZE}"

################################################################################
# Upload to Remote (Optional)
################################################################################
if [ "$UPLOAD_REMOTE" = true ]; then
    echo ""
    echo -e "${BLUE}Uploading to remote storage...${NC}"

    if command -v rclone &> /dev/null; then
        # Upload with rclone (configure first: rclone config)
        rclone copy "${SNAPSHOT_NAME}.tar.gz" remote:mt5-backups/snapshots/ --progress
        echo -e "${GREEN}✓${NC} Uploaded to remote storage"
    else
        echo -e "${YELLOW}⚠${NC}  rclone not installed, skipping remote upload"
        echo -e "${YELLOW}   Install: curl https://rclone.org/install.sh | sudo bash${NC}"
    fi
fi

################################################################################
# Cleanup Old Snapshots
################################################################################
echo ""
echo -e "${BLUE}Cleaning up old snapshots...${NC}"
# Keep last 10 snapshots
ls -t "${BACKUP_BASE_DIR}"/mt5-snapshot-*.tar.gz | tail -n +11 | xargs rm -f 2>/dev/null || true
# Keep last 5 uncompressed snapshots
ls -td "${BACKUP_BASE_DIR}"/mt5-snapshot-*/ | tail -n +6 | xargs rm -rf 2>/dev/null || true
echo -e "${GREEN}✓${NC} Old snapshots cleaned"

################################################################################
# Summary
################################################################################
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Snapshot Complete! 🎉                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}📦 Compressed snapshot:${NC} ${SNAPSHOT_NAME}.tar.gz"
echo -e "${GREEN}📏 Size:${NC} ${SNAPSHOT_SIZE}"
echo -e "${GREEN}📁 Location:${NC} ${BACKUP_BASE_DIR}/"
echo ""
echo -e "${BLUE}To view snapshot info:${NC}"
echo -e "  cat ${SNAPSHOT_DIR}/SNAPSHOT_INFO.txt"
echo ""
echo -e "${BLUE}To restore:${NC}"
echo -e "  ./scripts/backup/restore-snapshot.sh ${SNAPSHOT_NAME}"
echo ""

# Save snapshot metadata to central index
SNAPSHOT_INDEX="${BACKUP_BASE_DIR}/snapshots-index.txt"
{
    echo "$(date +%Y-%m-%d_%H:%M:%S) | ${SNAPSHOT_NAME} | ${SNAPSHOT_SIZE} | $(hostname)"
} >> "${SNAPSHOT_INDEX}"

exit 0
