#!/bin/bash
# Generate PgBouncer userlist with MD5 password hash
# Usage: ./generate_userlist.sh

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== PgBouncer Userlist Generator ===${NC}\n"

# Check if .env file exists
if [[ ! -f .env ]]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Source .env file
set -a
source .env
set +a

# Get credentials from .env
POSTGRES_USER="${POSTGRES_USER:-trader}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD}"

if [[ -z "$POSTGRES_PASSWORD" ]]; then
    echo -e "${RED}Error: POSTGRES_PASSWORD not set in .env${NC}"
    exit 1
fi

echo -e "Generating MD5 hash for user: ${YELLOW}${POSTGRES_USER}${NC}"

# Generate MD5 hash
# Format: md5(password + username)
PASSWORD_HASH=$(echo -n "${POSTGRES_PASSWORD}${POSTGRES_USER}" | md5sum | awk '{print "md5"$1}')

echo -e "Password hash: ${YELLOW}${PASSWORD_HASH}${NC}\n"

# Create userlist.txt
USERLIST_FILE="pgbouncer/userlist.txt"

cat > "$USERLIST_FILE" <<EOF
;; PgBouncer User List
;; Format: "username" "password_hash"
;;
;; Auto-generated on $(date)
;; DO NOT EDIT MANUALLY - Run ./generate_userlist.sh to regenerate

"${POSTGRES_USER}" "${PASSWORD_HASH}"
EOF

echo -e "${GREEN}✓ Created ${USERLIST_FILE}${NC}"

# Set proper permissions
chmod 600 "$USERLIST_FILE"
echo -e "${GREEN}✓ Set permissions (600) on ${USERLIST_FILE}${NC}\n"

# Display contents
echo -e "${YELLOW}Contents of ${USERLIST_FILE}:${NC}"
cat "$USERLIST_FILE" | grep -v "^;;" | grep -v "^$"

echo -e "\n${GREEN}=== Userlist generation complete ===${NC}"
echo -e "\nNext steps:"
echo -e "  1. Review the userlist: cat ${USERLIST_FILE}"
echo -e "  2. Start PgBouncer: docker-compose up -d pgbouncer"
echo -e "  3. Test connection: psql -h localhost -p 6432 -U ${POSTGRES_USER} -d mt5_trading"
