#!/bin/bash
set -euo pipefail

# MT5 Trading - Network Load Testing Script
# Tests network stability under maximum load conditions

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/network_load_test_$(date +%Y%m%d_%H%M%S).log"
RESULTS_FILE="${SCRIPT_DIR}/logs/network_load_results_$(date +%Y%m%d_%H%M%S).csv"

# Test parameters
DURATION=${1:-300}  # Default 5 minutes
CONCURRENT_REQUESTS=${2:-100}
API_ENDPOINT=${3:-"http://localhost:18003/health"}

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

print_header "🔥 MT5 Trading - Network Load Test"
log "Starting network load test..."
log "Duration: ${DURATION}s, Concurrent: ${CONCURRENT_REQUESTS}, Endpoint: ${API_ENDPOINT}"

# Initialize results file
echo "timestamp,response_time_ms,status_code,db_connections,network_errors" > "$RESULTS_FILE"

# ============================================================
# Pre-test Network Baseline
# ============================================================
echo -e "${BLUE}📊 Establishing network baseline...${NC}"

# Get initial metrics
INITIAL_RX_BYTES=0
INITIAL_TX_BYTES=0
NETWORK_NAME="mt5-process-core_default"
DOCKER_IFACE=$(ip -o link show | grep "br-" | head -1 | awk -F': ' '{print $2}' || echo "")

if [ -n "$DOCKER_IFACE" ]; then
    INITIAL_RX_BYTES=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_bytes" 2>/dev/null || echo "0")
    INITIAL_TX_BYTES=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_bytes" 2>/dev/null || echo "0")
    echo "  Initial RX: $((INITIAL_RX_BYTES / 1024 / 1024)) MB"
    echo "  Initial TX: $((INITIAL_TX_BYTES / 1024 / 1024)) MB"
fi

# Get initial DB connections
if docker ps --filter "name=mt5_db" --format "{{.Names}}" | grep -q "mt5_db"; then
    INITIAL_DB_CONN=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
    echo "  Initial DB Connections: $INITIAL_DB_CONN"
fi

echo ""

# ============================================================
# Network Load Test Functions
# ============================================================

# Function to make a single request
make_request() {
    local start_time=$(date +%s%3N)
    local response=$(curl -s -o /dev/null -w "%{http_code}:%{time_total}" "$API_ENDPOINT" 2>/dev/null || echo "000:99.999")
    local end_time=$(date +%s%3N)
    
    local status_code=$(echo "$response" | cut -d: -f1)
    local response_time=$(echo "$response" | cut -d: -f2)
    local response_time_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "9999")
    
    echo "${status_code},${response_time_ms}"
}

# Function to monitor network during test
monitor_network() {
    local duration=$1
    local interval=5
    local elapsed=0
    
    echo -e "${CYAN}🔍 Monitoring network metrics...${NC}"
    
    while [ $elapsed -lt $duration ]; do
        sleep $interval
        elapsed=$((elapsed + interval))
        
        # Get current metrics
        if [ -n "$DOCKER_IFACE" ]; then
            CURRENT_RX_BYTES=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_bytes" 2>/dev/null || echo "0")
            CURRENT_TX_BYTES=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_bytes" 2>/dev/null || echo "0")
            RX_ERRORS=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_errors" 2>/dev/null || echo "0")
            TX_ERRORS=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_errors" 2>/dev/null || echo "0")
            
            # Calculate throughput
            RX_DIFF=$((CURRENT_RX_BYTES - INITIAL_RX_BYTES))
            TX_DIFF=$((CURRENT_TX_BYTES - INITIAL_TX_BYTES))
            RX_MBPS=$(echo "scale=2; $RX_DIFF / $elapsed / 1024 / 1024 * 8" | bc 2>/dev/null || echo "0")
            TX_MBPS=$(echo "scale=2; $TX_DIFF / $elapsed / 1024 / 1024 * 8" | bc 2>/dev/null || echo "0")
            
            log "Network: RX=${RX_MBPS}Mbps TX=${TX_MBPS}Mbps Errors=RX:${RX_ERRORS},TX:${TX_ERRORS}"
        fi
        
        # Get DB connection count
        if docker ps --filter "name=mt5_db" --format "{{.Names}}" | grep -q "mt5_db"; then
            DB_CONN=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
            log "DB Connections: $DB_CONN"
        fi
        
        # Check container health
        for container in mt5_db mt5_api mt5_pgbouncer; do
            if docker ps --filter "name=$container" --format "{{.Names}}" | grep -q "$container"; then
                HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
                if [ "$HEALTH" != "healthy" ] && [ "$HEALTH" != "N/A" ]; then
                    log "WARNING: $container health is $HEALTH"
                fi
            fi
        done
    done
}

# ============================================================
# Execute Load Test
# ============================================================
print_header "🚀 Starting Load Test"

echo "Test Configuration:"
echo "  Duration: ${DURATION}s"
echo "  Concurrent Requests: ${CONCURRENT_REQUESTS}"
echo "  Target Endpoint: ${API_ENDPOINT}"
echo ""

# Start background network monitor
monitor_network "$DURATION" &
MONITOR_PID=$!

# Arrays for statistics
declare -a response_times=()
declare -a status_codes=()
total_requests=0
successful_requests=0
failed_requests=0

echo -e "${GREEN}📡 Sending requests...${NC}"
START_TIME=$(date +%s)

# Main load test loop
while [ $(($(date +%s) - START_TIME)) -lt $DURATION ]; do
    # Send concurrent requests
    for i in $(seq 1 $CONCURRENT_REQUESTS); do
        (
            result=$(make_request)
            status=$(echo "$result" | cut -d, -f1)
            response_time=$(echo "$result" | cut -d, -f2)
            
            # Get current DB connections
            db_conn="N/A"
            if docker ps --filter "name=mt5_db" --format "{{.Names}}" | grep -q "mt5_db"; then
                db_conn=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "N/A")
            fi
            
            # Get network errors
            net_errors=0
            if [ -n "$DOCKER_IFACE" ]; then
                rx_err=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_errors" 2>/dev/null || echo "0")
                tx_err=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_errors" 2>/dev/null || echo "0")
                net_errors=$((rx_err + tx_err))
            fi
            
            # Record result
            echo "$(date +%s),$response_time,$status,$db_conn,$net_errors" >> "$RESULTS_FILE"
        ) &
    done
    
    # Wait for batch to complete
    wait
    
    total_requests=$((total_requests + CONCURRENT_REQUESTS))
    
    # Progress indicator
    elapsed=$(($(date +%s) - START_TIME))
    echo -ne "  Progress: ${elapsed}s / ${DURATION}s (${total_requests} requests)\r"
done

echo ""
echo -e "${GREEN}✓${NC} Load test completed"

# Stop background monitor
kill $MONITOR_PID 2>/dev/null || true
wait $MONITOR_PID 2>/dev/null || true

# ============================================================
# Analyze Results
# ============================================================
print_header "📊 Test Results Analysis"

# Calculate statistics from results file
if [ -f "$RESULTS_FILE" ]; then
    # Count successful/failed requests
    total_requests=$(tail -n +2 "$RESULTS_FILE" | wc -l)
    successful_requests=$(tail -n +2 "$RESULTS_FILE" | awk -F, '$3 == 200' | wc -l)
    failed_requests=$((total_requests - successful_requests))
    
    echo "Request Statistics:"
    echo "  Total Requests: $total_requests"
    echo "  Successful (200): $successful_requests"
    echo "  Failed: $failed_requests"
    
    if [ $total_requests -gt 0 ]; then
        success_rate=$(echo "scale=2; $successful_requests * 100 / $total_requests" | bc)
        echo "  Success Rate: ${success_rate}%"
    fi
    
    echo ""
    
    # Calculate response time statistics
    echo "Response Time Statistics (ms):"
    tail -n +2 "$RESULTS_FILE" | awk -F, '$3 == 200 {print $2}' | sort -n > /tmp/response_times.txt
    
    if [ -s /tmp/response_times.txt ]; then
        MIN_RT=$(head -1 /tmp/response_times.txt)
        MAX_RT=$(tail -1 /tmp/response_times.txt)
        AVG_RT=$(awk '{sum+=$1; count++} END {printf "%.2f", sum/count}' /tmp/response_times.txt)
        
        # Calculate percentiles
        TOTAL_LINES=$(wc -l < /tmp/response_times.txt)
        P50_LINE=$((TOTAL_LINES / 2))
        P90_LINE=$((TOTAL_LINES * 90 / 100))
        P95_LINE=$((TOTAL_LINES * 95 / 100))
        P99_LINE=$((TOTAL_LINES * 99 / 100))
        
        P50_RT=$(sed -n "${P50_LINE}p" /tmp/response_times.txt)
        P90_RT=$(sed -n "${P90_LINE}p" /tmp/response_times.txt)
        P95_RT=$(sed -n "${P95_LINE}p" /tmp/response_times.txt)
        P99_RT=$(sed -n "${P99_LINE}p" /tmp/response_times.txt)
        
        echo "  Min: ${MIN_RT}ms"
        echo "  Max: ${MAX_RT}ms"
        echo "  Average: ${AVG_RT}ms"
        echo "  P50 (Median): ${P50_RT}ms"
        echo "  P90: ${P90_RT}ms"
        echo "  P95: ${P95_RT}ms"
        echo "  P99: ${P99_RT}ms"
        
        rm -f /tmp/response_times.txt
    fi
fi

echo ""

# Network throughput statistics
if [ -n "$DOCKER_IFACE" ]; then
    FINAL_RX_BYTES=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_bytes" 2>/dev/null || echo "0")
    FINAL_TX_BYTES=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_bytes" 2>/dev/null || echo "0")
    
    TOTAL_RX_MB=$(( (FINAL_RX_BYTES - INITIAL_RX_BYTES) / 1024 / 1024 ))
    TOTAL_TX_MB=$(( (FINAL_TX_BYTES - INITIAL_TX_BYTES) / 1024 / 1024 ))
    
    AVG_RX_MBPS=$(echo "scale=2; $TOTAL_RX_MB * 8 / $DURATION" | bc 2>/dev/null || echo "0")
    AVG_TX_MBPS=$(echo "scale=2; $TOTAL_TX_MB * 8 / $DURATION" | bc 2>/dev/null || echo "0")
    
    echo "Network Throughput:"
    echo "  Total RX: ${TOTAL_RX_MB} MB"
    echo "  Total TX: ${TOTAL_TX_MB} MB"
    echo "  Average RX: ${AVG_RX_MBPS} Mbps"
    echo "  Average TX: ${AVG_TX_MBPS} Mbps"
    
    # Check for errors
    FINAL_RX_ERRORS=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_errors" 2>/dev/null || echo "0")
    FINAL_TX_ERRORS=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_errors" 2>/dev/null || echo "0")
    FINAL_RX_DROPPED=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/rx_dropped" 2>/dev/null || echo "0")
    FINAL_TX_DROPPED=$(cat "/sys/class/net/$DOCKER_IFACE/statistics/tx_dropped" 2>/dev/null || echo "0")
    
    echo ""
    echo "Network Errors:"
    echo "  RX Errors: $FINAL_RX_ERRORS"
    echo "  TX Errors: $FINAL_TX_ERRORS"
    echo "  RX Dropped: $FINAL_RX_DROPPED"
    echo "  TX Dropped: $FINAL_TX_DROPPED"
fi

echo ""

# Database connection statistics
if docker ps --filter "name=mt5_db" --format "{{.Names}}" | grep -q "mt5_db"; then
    FINAL_DB_CONN=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
    MAX_DB_CONN=$(tail -n +2 "$RESULTS_FILE" | awk -F, '{print $4}' | sort -n | tail -1)
    
    echo "Database Connections:"
    echo "  Current: $FINAL_DB_CONN"
    echo "  Peak during test: $MAX_DB_CONN"
fi

# ============================================================
# Health Check After Load
# ============================================================
print_header "🏥 Post-Load Health Check"

echo "Waiting 10 seconds for system to stabilize..."
sleep 10

echo ""
echo "Container Status:"
for container in mt5_db mt5_api mt5_pgbouncer; do
    if docker ps --filter "name=$container" --format "{{.Names}}" | grep -q "$container"; then
        STATUS=$(docker inspect --format='{{.State.Status}}' "$container")
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
        
        if [ "$STATUS" = "running" ]; then
            if [ "$HEALTH" = "healthy" ] || [ "$HEALTH" = "N/A" ]; then
                echo -e "  $container: ${GREEN}✓ Running${NC}"
            else
                echo -e "  $container: ${YELLOW}⚠ Running but $HEALTH${NC}"
            fi
        else
            echo -e "  $container: ${RED}✗ $STATUS${NC}"
        fi
    else
        echo -e "  $container: ${RED}✗ Not found${NC}"
    fi
done

# ============================================================
# Summary and Recommendations
# ============================================================
print_header "📋 Summary and Recommendations"

ISSUES=0

# Check success rate
if [ $total_requests -gt 0 ]; then
    success_rate=$(echo "scale=2; $successful_requests * 100 / $total_requests" | bc)
    success_rate_int=$(echo "$success_rate" | cut -d. -f1)
    
    if [ "$success_rate_int" -ge 99 ]; then
        echo -e "${GREEN}✓${NC} Excellent success rate (${success_rate}%)"
    elif [ "$success_rate_int" -ge 95 ]; then
        echo -e "${YELLOW}⚠${NC} Good success rate (${success_rate}%) - minor issues"
        ((ISSUES++))
    else
        echo -e "${RED}✗${NC} Poor success rate (${success_rate}%) - needs attention"
        ((ISSUES++))
    fi
fi

# Check response times
if [ -n "${P95_RT:-}" ]; then
    P95_INT=$(echo "$P95_RT" | cut -d. -f1)
    if [ "$P95_INT" -lt 100 ]; then
        echo -e "${GREEN}✓${NC} Excellent response times (P95: ${P95_RT}ms)"
    elif [ "$P95_INT" -lt 500 ]; then
        echo -e "${YELLOW}⚠${NC} Acceptable response times (P95: ${P95_RT}ms)"
    else
        echo -e "${RED}✗${NC} High response times (P95: ${P95_RT}ms)"
        ((ISSUES++))
    fi
fi

# Check network errors
if [ "${FINAL_RX_ERRORS:-0}" -gt 0 ] || [ "${FINAL_TX_ERRORS:-0}" -gt 0 ]; then
    echo -e "${RED}✗${NC} Network errors detected during test"
    ((ISSUES++))
else
    echo -e "${GREEN}✓${NC} No network errors detected"
fi

# Check packet drops
TOTAL_DROPPED=$((${FINAL_RX_DROPPED:-0} + ${FINAL_TX_DROPPED:-0}))
if [ "$TOTAL_DROPPED" -gt 100 ]; then
    echo -e "${YELLOW}⚠${NC} Significant packet drops ($TOTAL_DROPPED)"
    ((ISSUES++))
else
    echo -e "${GREEN}✓${NC} Minimal packet drops"
fi

echo ""
echo "Detailed results saved to:"
echo "  Log: $LOG_FILE"
echo "  CSV: $RESULTS_FILE"

echo ""
if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ Network is stable under maximum load!${NC}"
    log "SUCCESS: Network load test passed"
    exit 0
else
    echo -e "${YELLOW}⚠ Found $ISSUES issue(s) under load${NC}"
    echo ""
    echo "Recommendations:"
    echo "  1. Review detailed logs for error patterns"
    echo "  2. Consider increasing connection pool sizes"
    echo "  3. Check database query performance"
    echo "  4. Monitor system resources (CPU, memory, disk I/O)"
    echo "  5. Consider implementing rate limiting"
    log "WARNING: Network load test found $ISSUES issue(s)"
    exit 1
fi
