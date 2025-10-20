#!/bin/bash
################################################################################
# MT5 Trading - Snapshot Restore System
#
# Restores a complete snapshot of the repository
#
# Usage: ./restore-snapshot.sh SNAPSHOT_NAME [options]
#   -f, --force         Force restore without confirmation
#   --skip-db           Skip database restore
#   --skip-volumes      Skip volume restore
#   --skip-git          Skip git restore
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_BASE_DIR="/home/felipe/backups/snapshots"
RESTORE_DIR="/tmp/mt5-restore-$$"
SKIP_DB=false
SKIP_VOLUMES=false
SKIP_GIT=false
FORCE=false

# Check if snapshot name provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Snapshot name required${NC}"
    echo "Usage: $0 SNAPSHOT_NAME [options]"
    echo ""
    echo "Available snapshots:"
    ls -1 "${BACKUP_BASE_DIR}"/mt5-snapshot-*.tar.gz 2>/dev/null | xargs -n 1 basename | sed 's/.tar.gz$//' || echo "  No snapshots found"
    exit 1
fi

SNAPSHOT_NAME="$1"
shift

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --skip-volumes)
            SKIP_VOLUMES=true
            shift
            ;;
        --skip-git)
            SKIP_GIT=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 SNAPSHOT_NAME [options]"
            echo "  -f, --force        Force restore without confirmation"
            echo "  --skip-db          Skip database restore"
            echo "  --skip-volumes     Skip volume restore"
            echo "  --skip-git         Skip git restore"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

SNAPSHOT_FILE="${BACKUP_BASE_DIR}/${SNAPSHOT_NAME}.tar.gz"

if [ ! -f "$SNAPSHOT_FILE" ]; then
    echo -e "${RED}Error: Snapshot not found: ${SNAPSHOT_FILE}${NC}"
    echo ""
    echo "Available snapshots:"
    ls -1 "${BACKUP_BASE_DIR}"/mt5-snapshot-*.tar.gz 2>/dev/null | xargs -n 1 basename | sed 's/.tar.gz$//' || echo "  No snapshots found"
    exit 1
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           MT5 Trading - Snapshot Restore Tool                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}⚠️  WARNING: This will restore from snapshot:${NC}"
echo -e "${YELLOW}   ${SNAPSHOT_NAME}${NC}"
echo ""

# Extract and show snapshot info
mkdir -p "${RESTORE_DIR}"
tar xzf "${SNAPSHOT_FILE}" -C "${RESTORE_DIR}"
SNAPSHOT_DIR="${RESTORE_DIR}/${SNAPSHOT_NAME}"

if [ -f "${SNAPSHOT_DIR}/SNAPSHOT_INFO.txt" ]; then
    echo -e "${BLUE}Snapshot Information:${NC}"
    head -20 "${SNAPSHOT_DIR}/SNAPSHOT_INFO.txt"
    echo ""
fi

# Confirmation
if [ "$FORCE" != true ]; then
    echo -e "${RED}⚠️  This will REPLACE your current data!${NC}"
    echo -e "${YELLOW}Make sure you have a backup before proceeding.${NC}"
    echo ""
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        echo -e "${YELLOW}Restore cancelled.${NC}"
        rm -rf "${RESTORE_DIR}"
        exit 0
    fi
fi

################################################################################
# 1. Verify Checksums
################################################################################
echo ""
echo -e "${BLUE}[1/5]${NC} Verifying snapshot integrity..."
cd "${SNAPSHOT_DIR}"
if sha256sum -c checksums.sha256 --quiet; then
    echo -e "${GREEN}✓${NC} Snapshot integrity verified"
else
    echo -e "${RED}✗${NC} Checksum verification failed!"
    echo -e "${RED}   Snapshot may be corrupted. Aborting restore.${NC}"
    rm -rf "${RESTORE_DIR}"
    exit 1
fi

################################################################################
# 2. Stop Services
################################################################################
echo -e "${BLUE}[2/5]${NC} Stopping services..."
cd /home/felipe/mt5-trading-db
docker-compose down
echo -e "${GREEN}✓${NC} Services stopped"

################################################################################
# 3. Restore Git Repository
################################################################################
if [ "$SKIP_GIT" != true ]; then
    echo -e "${BLUE}[3/5]${NC} Restoring git repository..."

    # Backup current .git (just in case)
    if [ -d ".git" ]; then
        mv .git .git.backup.$(date +%s)
    fi

    # Clone from bundle
    git clone "${SNAPSHOT_DIR}/repository.bundle" . --quiet || true

    echo -e "${GREEN}✓${NC} Git repository restored"
else
    echo -e "${BLUE}[3/5]${NC} Skipping git restore"
fi

################################################################################
# 4. Restore Database
################################################################################
if [ "$SKIP_DB" != true ]; then
    echo -e "${BLUE}[4/5]${NC} Restoring database..."

    # Start only database
    docker-compose up -d db
    sleep 10

    # Wait for database to be ready
    echo -e "  Waiting for database..."
    until docker exec mt5_db pg_isready -U trader > /dev/null 2>&1; do
        sleep 2
    done

    # Restore database
    if [ -f "${SNAPSHOT_DIR}/database-full.sql.gz" ]; then
        echo -e "  Restoring full database..."
        gunzip -c "${SNAPSHOT_DIR}/database-full.sql.gz" | docker exec -i mt5_db psql -U trader
        echo -e "${GREEN}✓${NC} Database restored"
    else
        echo -e "${YELLOW}⚠${NC}  No database backup found in snapshot"
    fi

    docker-compose stop db
else
    echo -e "${BLUE}[4/5]${NC} Skipping database restore"
fi

################################################################################
# 5. Restore Docker Volumes
################################################################################
if [ "$SKIP_VOLUMES" != true ]; then
    echo -e "${BLUE}[5/5]${NC} Restoring Docker volumes..."

    if [ -d "${SNAPSHOT_DIR}/volumes" ]; then
        for volume_archive in "${SNAPSHOT_DIR}"/volumes/*.tar.gz; do
            if [ -f "$volume_archive" ]; then
                volume_name=$(basename "$volume_archive" .tar.gz)
                echo -e "  Restoring ${volume_name}..."

                # Remove existing volume
                docker volume rm "$volume_name" 2>/dev/null || true

                # Create new volume
                docker volume create "$volume_name" >/dev/null

                # Restore data
                docker run --rm \
                    -v "${volume_name}:/data" \
                    -v "${SNAPSHOT_DIR}/volumes:/backup:ro" \
                    alpine \
                    tar xzf "/backup/${volume_name}.tar.gz" -C /data

                echo -e "${GREEN}  ✓${NC} ${volume_name}"
            fi
        done
        echo -e "${GREEN}✓${NC} Docker volumes restored"
    else
        echo -e "${YELLOW}⚠${NC}  No volume backups found in snapshot"
    fi
else
    echo -e "${BLUE}[5/5]${NC} Skipping volume restore"
fi

################################################################################
# Restore Configuration Files
################################################################################
echo ""
echo -e "${BLUE}Restoring configuration files...${NC}"
if [ -d "${SNAPSHOT_DIR}/config" ]; then
    cp -r "${SNAPSHOT_DIR}"/config/* . 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Configuration files restored"
fi

################################################################################
# Start Services
################################################################################
echo ""
echo -e "${BLUE}Starting services...${NC}"
docker-compose up -d
echo -e "${GREEN}✓${NC} Services started"

################################################################################
# Cleanup
################################################################################
echo ""
echo -e "${BLUE}Cleaning up...${NC}"
rm -rf "${RESTORE_DIR}"
echo -e "${GREEN}✓${NC} Cleanup complete"

################################################################################
# Summary
################################################################################
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                   Restore Complete! 🎉                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}✓${NC} Snapshot ${SNAPSHOT_NAME} restored successfully"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Verify services are running: docker-compose ps"
echo -e "  2. Check logs: docker-compose logs -f"
echo -e "  3. Test API: curl http://localhost:8001/health"
echo ""

exit 0
