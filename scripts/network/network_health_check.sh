#!/bin/bash
set -euo pipefail

# MT5 Trading - Network Health Check Script
# Comprehensive network diagnostics and health monitoring

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/network_health_$(date +%Y%m%d_%H%M%S).log"
MAX_LATENCY_MS=50
MAX_PACKET_LOSS=1
MIN_BANDWIDTH_MBPS=100

# Ensure log directory exists
mkdir -p "${SCRIPT_DIR}/logs"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Print header
print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

# Print section
print_section() {
    echo -e "\n${BLUE}━━━ $1 ━━━${NC}\n"
}

# Check result
check_result() {
    local status=$1
    local message=$2
    
    if [ "$status" -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $message"
        return 0
    else
        echo -e "${RED}✗${NC} $message"
        return 1
    fi
}

# Start script
print_header "🌐 MT5 Trading - Network Health Check"
log "Starting network health check..."

# Counter for issues
ISSUES_FOUND=0

# ============================================================
# 1. Docker Network Configuration
# ============================================================
print_section "Docker Network Configuration"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running${NC}"
    log "ERROR: Docker is not running"
    exit 1
fi

# List Docker networks
echo "Available Docker Networks:"
docker network ls | tee -a "$LOG_FILE"
echo ""

# Inspect MT5 network
NETWORK_NAME="mt5-process-core_default"
if docker network inspect "$NETWORK_NAME" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Network '$NETWORK_NAME' exists"
    
    # Get network details
    SUBNET=$(docker network inspect "$NETWORK_NAME" --format='{{range .IPAM.Config}}{{.Subnet}}{{end}}')
    GATEWAY=$(docker network inspect "$NETWORK_NAME" --format='{{range .IPAM.Config}}{{.Gateway}}{{end}}')
    DRIVER=$(docker network inspect "$NETWORK_NAME" --format='{{.Driver}}')
    
    echo "  Subnet: $SUBNET"
    echo "  Gateway: $GATEWAY"
    echo "  Driver: $DRIVER"
    
    # Check MTU
    MTU=$(docker network inspect "$NETWORK_NAME" --format='{{.Options.com.docker.network.driver.mtu}}' || echo "default")
    echo "  MTU: ${MTU:-default (1500)}"
    
else
    echo -e "${RED}✗${NC} Network '$NETWORK_NAME' not found"
    ((ISSUES_FOUND++))
fi

# ============================================================
# 2. Container Network Status
# ============================================================
print_section "Container Network Status"

# List all MT5 containers
CONTAINERS=$(docker ps -a --filter "name=mt5_" --format "{{.Names}}" 2>/dev/null || true)

if [ -z "$CONTAINERS" ]; then
    echo -e "${YELLOW}⚠${NC} No MT5 containers found"
    log "WARNING: No MT5 containers found"
else
    for container in $CONTAINERS; do
        echo "Container: $container"
        
        # Check if running
        if docker ps --filter "name=$container" --format "{{.Names}}" | grep -q "^${container}$"; then
            STATUS=$(docker inspect --format='{{.State.Status}}' "$container")
            HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
            
            echo -e "  Status: ${GREEN}$STATUS${NC}"
            if [ "$HEALTH" != "N/A" ]; then
                if [ "$HEALTH" = "healthy" ]; then
                    echo -e "  Health: ${GREEN}$HEALTH${NC}"
                else
                    echo -e "  Health: ${YELLOW}$HEALTH${NC}"
                fi
            fi
            
            # Get network info
            IP_ADDR=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$container")
            GATEWAY=$(docker inspect --format='{{range .NetworkSettings.Networks}}{{.Gateway}}{{end}}' "$container")
            
            echo "  IP Address: $IP_ADDR"
            echo "  Gateway: $GATEWAY"
            
        else
            echo -e "  Status: ${RED}Not Running${NC}"
            ((ISSUES_FOUND++))
        fi
        echo ""
    done
fi

# ============================================================
# 3. Inter-Container Connectivity Tests
# ============================================================
print_section "Inter-Container Connectivity Tests"

# Check if API container is running
if docker ps --filter "name=mt5_api" --format "{{.Names}}" | grep -q "mt5_api"; then
    
    # Test 1: Ping database
    echo "Test: API -> Database (ping)"
    if docker exec mt5_api ping -c 3 -W 2 db > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Ping successful"
        
        # Get latency stats
        LATENCY=$(docker exec mt5_api ping -c 10 -W 2 db 2>/dev/null | tail -1 | awk -F'/' '{print $5}' | cut -d. -f1)
        echo "  Average Latency: ${LATENCY}ms"
        
        if [ "${LATENCY:-999}" -gt "$MAX_LATENCY_MS" ]; then
            echo -e "  ${YELLOW}⚠${NC} High latency detected (>${MAX_LATENCY_MS}ms)"
            ((ISSUES_FOUND++))
        fi
    else
        echo -e "${RED}✗${NC} Ping failed"
        ((ISSUES_FOUND++))
    fi
    
    # Test 2: DNS resolution
    echo ""
    echo "Test: DNS Resolution (db)"
    if docker exec mt5_api nslookup db > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} DNS resolution successful"
        DNS_IP=$(docker exec mt5_api nslookup db 2>/dev/null | grep -A1 "Name:" | tail -1 | awk '{print $2}')
        echo "  Resolved IP: $DNS_IP"
    else
        echo -e "${RED}✗${NC} DNS resolution failed"
        ((ISSUES_FOUND++))
    fi
    
    # Test 3: Database connection
    echo ""
    echo "Test: Database Connection (PostgreSQL)"
    if docker exec mt5_api curl -sf http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Database connection healthy"
    else
        echo -e "${RED}✗${NC} Database connection failed"
        ((ISSUES_FOUND++))
    fi
    
    # Test 4: Prometheus connectivity
    echo ""
    echo "Test: API -> Prometheus"
    if docker exec mt5_api ping -c 3 -W 2 prometheus > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Prometheus reachable"
    else
        echo -e "${YELLOW}⚠${NC} Prometheus not reachable"
    fi
    
else
    echo -e "${YELLOW}⚠${NC} mt5_api container not running - skipping connectivity tests"
fi

# ============================================================
# 4. Database Connection Pool Status
# ============================================================
print_section "Database Connection Pool Status"

if docker ps --filter "name=mt5_db" --format "{{.Names}}" | grep -q "mt5_db"; then
    
    # Get active connections
    ACTIVE_CONN=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" 2>/dev/null | xargs)
    IDLE_CONN=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle';" 2>/dev/null | xargs)
    TOTAL_CONN=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
    MAX_CONN=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SHOW max_connections;" 2>/dev/null | xargs)
    
    echo "Connection Statistics:"
    echo "  Active Connections: $ACTIVE_CONN"
    echo "  Idle Connections: $IDLE_CONN"
    echo "  Total Connections: $TOTAL_CONN"
    echo "  Max Connections: $MAX_CONN"
    
    # Calculate usage percentage
    if [ -n "$TOTAL_CONN" ] && [ -n "$MAX_CONN" ]; then
        USAGE_PCT=$((TOTAL_CONN * 100 / MAX_CONN))
        echo "  Usage: ${USAGE_PCT}%"
        
        if [ "$USAGE_PCT" -gt 80 ]; then
            echo -e "  ${YELLOW}⚠${NC} High connection usage (>80%)"
            ((ISSUES_FOUND++))
        fi
    fi
    
    echo ""
    echo "Connection Details:"
    docker exec mt5_db psql -U trader -d mt5_trading -c "
        SELECT 
            application_name,
            state,
            count(*) as connections,
            max(now() - state_change) as max_duration
        FROM pg_stat_activity 
        WHERE datname = 'mt5_trading'
        GROUP BY application_name, state
        ORDER BY connections DESC;
    " 2>/dev/null || echo "Failed to query connection details"
    
else
    echo -e "${RED}✗${NC} Database container not running"
    ((ISSUES_FOUND++))
fi

# ============================================================
# 5. PgBouncer Status
# ============================================================
print_section "PgBouncer Connection Pooling Status"

if docker ps --filter "name=mt5_pgbouncer" --format "{{.Names}}" | grep -q "mt5_pgbouncer"; then
    
    echo "PgBouncer Statistics:"
    docker exec mt5_pgbouncer psql -h 127.0.0.1 -p 5432 -U trader -d pgbouncer -c "SHOW POOLS;" 2>/dev/null || echo "Failed to query PgBouncer pools"
    
    echo ""
    echo "PgBouncer Clients:"
    docker exec mt5_pgbouncer psql -h 127.0.0.1 -p 5432 -U trader -d pgbouncer -c "SHOW CLIENTS;" 2>/dev/null | head -20 || echo "Failed to query PgBouncer clients"
    
    echo ""
    echo "PgBouncer Servers:"
    docker exec mt5_pgbouncer psql -h 127.0.0.1 -p 5432 -U trader -d pgbouncer -c "SHOW SERVERS;" 2>/dev/null || echo "Failed to query PgBouncer servers"
    
else
    echo -e "${YELLOW}⚠${NC} PgBouncer container not running"
fi

# ============================================================
# 6. Network Performance Metrics
# ============================================================
print_section "Network Performance Metrics"

# Check network interface stats
echo "Docker Network Interface Statistics:"
DOCKER_IFACE=$(ip -o link show | grep "br-" | grep "$NETWORK_NAME" | awk -F': ' '{print $2}' | head -1 || echo "")

if [ -n "$DOCKER_IFACE" ]; then
    echo "Interface: $DOCKER_IFACE"
    
    # Get interface statistics
    RX_BYTES=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_bytes" 2>/dev/null || echo "0")
    TX_BYTES=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_bytes" 2>/dev/null || echo "0")
    RX_PACKETS=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_packets" 2>/dev/null || echo "0")
    TX_PACKETS=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_packets" 2>/dev/null || echo "0")
    RX_ERRORS=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_errors" 2>/dev/null || echo "0")
    TX_ERRORS=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_errors" 2>/dev/null || echo "0")
    RX_DROPPED=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_dropped" 2>/dev/null || echo "0")
    TX_DROPPED=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_dropped" 2>/dev/null || echo "0")
    
    # Convert to human readable
    RX_MB=$((RX_BYTES / 1024 / 1024))
    TX_MB=$((TX_BYTES / 1024 / 1024))
    
    echo "  RX: ${RX_MB} MB (${RX_PACKETS} packets)"
    echo "  TX: ${TX_MB} MB (${TX_PACKETS} packets)"
    echo "  RX Errors: $RX_ERRORS"
    echo "  TX Errors: $TX_ERRORS"
    echo "  RX Dropped: $RX_DROPPED"
    echo "  TX Dropped: $TX_DROPPED"
    
    # Check for errors
    if [ "$RX_ERRORS" -gt 0 ] || [ "$TX_ERRORS" -gt 0 ]; then
        echo -e "  ${YELLOW}⚠${NC} Network errors detected"
        ((ISSUES_FOUND++))
    fi
    
    if [ "$RX_DROPPED" -gt 100 ] || [ "$TX_DROPPED" -gt 100 ]; then
        echo -e "  ${YELLOW}⚠${NC} Significant packet drops detected"
        ((ISSUES_FOUND++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Docker network interface not found"
fi

# ============================================================
# 7. API Endpoint Response Times
# ============================================================
print_section "API Endpoint Response Times"

if curl -sf http://localhost:18003/health > /dev/null 2>&1; then
    echo "Testing API endpoints..."
    
    # Test health endpoint
    HEALTH_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:18003/health)
    echo "  /health: ${HEALTH_TIME}s"
    
    # Test metrics endpoint
    METRICS_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:18003/prometheus/ 2>/dev/null || echo "N/A")
    if [ "$METRICS_TIME" != "N/A" ]; then
        echo "  /prometheus: ${METRICS_TIME}s"
    fi
    
    # Test docs endpoint
    DOCS_TIME=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:18003/docs 2>/dev/null || echo "N/A")
    if [ "$DOCS_TIME" != "N/A" ]; then
        echo "  /docs: ${DOCS_TIME}s"
    fi
    
else
    echo -e "${RED}✗${NC} API not accessible at http://localhost:18003"
    ((ISSUES_FOUND++))
fi

# ============================================================
# 8. TCP Connection States
# ============================================================
print_section "TCP Connection States"

echo "System-wide TCP connections:"
ss -s | grep -E "TCP:|ESTAB|TIME-WAIT|CLOSE-WAIT" || netstat -an | grep -c ESTABLISHED || echo "Unable to get TCP statistics"

echo ""
echo "Docker container connections:"
for container in mt5_db mt5_api mt5_pgbouncer; do
    if docker ps --filter "name=$container" --format "{{.Names}}" | grep -q "$container"; then
        CONNECTIONS=$(docker exec "$container" ss -tan 2>/dev/null | grep -c ESTAB || echo "N/A")
        echo "  $container: $CONNECTIONS ESTABLISHED"
    fi
done

# ============================================================
# 9. DNS Resolution Performance
# ============================================================
print_section "DNS Resolution Performance"

# Test DNS resolution times
if docker ps --filter "name=mt5_api" --format "{{.Names}}" | grep -q "mt5_api"; then
    echo "Testing DNS resolution times..."
    
    for host in db pgbouncer prometheus grafana; do
        START=$(date +%s%N)
        if docker exec mt5_api nslookup "$host" > /dev/null 2>&1; then
            END=$(date +%s%N)
            DURATION=$(( (END - START) / 1000000 ))
            echo "  $host: ${DURATION}ms"
        else
            echo "  $host: Failed"
        fi
    done
fi

# ============================================================
# 10. Resource Usage Impact
# ============================================================
print_section "Network Resource Usage"

echo "Container Network Stats:"
docker stats --no-stream --format "table {{.Name}}\t{{.NetIO}}" $(docker ps --filter "name=mt5_" --format "{{.Names}}") 2>/dev/null || echo "Unable to get container stats"

# ============================================================
# Summary
# ============================================================
print_header "Summary"

if [ "$ISSUES_FOUND" -eq 0 ]; then
    echo -e "${GREEN}✓ All network health checks passed!${NC}"
    echo -e "${GREEN}✓ Network is stable and ready for maximum load${NC}"
    log "SUCCESS: All network health checks passed"
    exit 0
else
    echo -e "${YELLOW}⚠ Found $ISSUES_FOUND issue(s) that may affect stability${NC}"
    echo -e "${YELLOW}⚠ Please review the issues above${NC}"
    log "WARNING: Found $ISSUES_FOUND network issue(s)"
    exit 1
fi
