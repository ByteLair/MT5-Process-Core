#!/bin/bash
set -euo pipefail

# MT5 Trading - Continuous Network Monitor
# Real-time monitoring of network health and stability

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/logs/network_monitor_$(date +%Y%m%d).log"
INTERVAL=${1:-5}  # Monitoring interval in seconds

# Alert thresholds
MAX_RESPONSE_TIME=1000  # ms
MAX_DB_CONNECTIONS=180  # 90% of max_connections (200)
MAX_ERROR_RATE=5  # percent
MIN_SUCCESS_RATE=95  # percent

# Ensure log directory exists
mkdir -p "${SCRIPT_DIR}/logs"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" >> "$LOG_FILE"
}

# Alert function
alert() {
    local level=$1
    shift
    local message="$*"
    
    case $level in
        ERROR)
            echo -e "${RED}[ERROR] $message${NC}"
            log "ERROR: $message"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN] $message${NC}"
            log "WARN: $message"
            ;;
        INFO)
            echo -e "${GREEN}[INFO] $message${NC}"
            log "INFO: $message"
            ;;
        *)
            echo "$message"
            log "$message"
            ;;
    esac
}

# Function to get network interface
get_network_interface() {
    ip -o link show | grep "br-" | head -1 | awk -F': ' '{print $2}' || echo ""
}

# Function to get container IP
get_container_ip() {
    local container=$1
    docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$container" 2>/dev/null || echo "N/A"
}

# Function to check API health
check_api_health() {
    local start_time=$(date +%s%3N)
    local response=$(curl -s -o /dev/null -w "%{http_code}:%{time_total}" http://localhost:18003/health 2>/dev/null || echo "000:99.999")
    local end_time=$(date +%s%3N)
    
    local status_code=$(echo "$response" | cut -d: -f1)
    local response_time=$(echo "$response" | cut -d: -f2)
    local response_time_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "9999")
    
    echo "${status_code}:${response_time_ms}"
}

# Function to get DB connection count
get_db_connections() {
    if docker ps --filter "name=mt5_db" --format "{{.Names}}" | grep -q "mt5_db"; then
        docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "0"
    else
        echo "0"
    fi
}

# Function to get network stats
get_network_stats() {
    local iface=$1
    
    if [ -n "$iface" ] && [ -d "/sys/class/net/$iface" ]; then
        local rx_bytes=$(cat "/sys/class/net/$iface/statistics/rx_bytes" 2>/dev/null || echo "0")
        local tx_bytes=$(cat "/sys/class/net/$iface/statistics/tx_bytes" 2>/dev/null || echo "0")
        local rx_packets=$(cat "/sys/class/net/$iface/statistics/rx_packets" 2>/dev/null || echo "0")
        local tx_packets=$(cat "/sys/class/net/$iface/statistics/tx_packets" 2>/dev/null || echo "0")
        local rx_errors=$(cat "/sys/class/net/$iface/statistics/rx_errors" 2>/dev/null || echo "0")
        local tx_errors=$(cat "/sys/class/net/$iface/statistics/tx_errors" 2>/dev/null || echo "0")
        local rx_dropped=$(cat "/sys/class/net/$iface/statistics/rx_dropped" 2>/dev/null || echo "0")
        local tx_dropped=$(cat "/sys/class/net/$iface/statistics/tx_dropped" 2>/dev/null || echo "0")
        
        echo "${rx_bytes}:${tx_bytes}:${rx_packets}:${tx_packets}:${rx_errors}:${tx_errors}:${rx_dropped}:${tx_dropped}"
    else
        echo "0:0:0:0:0:0:0:0"
    fi
}

# Function to calculate throughput
calculate_throughput() {
    local prev_rx=$1
    local prev_tx=$2
    local current_rx=$3
    local current_tx=$4
    local interval=$5
    
    local rx_diff=$((current_rx - prev_rx))
    local tx_diff=$((current_tx - prev_tx))
    
    # Convert to Mbps
    local rx_mbps=$(echo "scale=2; $rx_diff * 8 / $interval / 1024 / 1024" | bc 2>/dev/null || echo "0")
    local tx_mbps=$(echo "scale=2; $tx_diff * 8 / $interval / 1024 / 1024" | bc 2>/dev/null || echo "0")
    
    echo "${rx_mbps}:${tx_mbps}"
}

# Function to check container health
check_container_health() {
    local container=$1
    
    if docker ps --filter "name=$container" --format "{{.Names}}" | grep -q "^${container}$"; then
        local status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
        local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
        
        echo "${status}:${health}"
    else
        echo "not_running:N/A"
    fi
}

# Clear screen and show header
clear
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}    MT5 Trading - Real-Time Network Monitor${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "Monitoring interval: ${INTERVAL}s | Log: ${LOG_FILE}"
echo -e "Press Ctrl+C to stop"
echo ""

log "Network monitoring started (interval: ${INTERVAL}s)"

# Initialize variables
NETWORK_IFACE=$(get_network_interface)
PREV_STATS=$(get_network_stats "$NETWORK_IFACE")
PREV_RX=$(echo "$PREV_STATS" | cut -d: -f1)
PREV_TX=$(echo "$PREV_STATS" | cut -d: -f2)
PREV_TIME=$(date +%s)

# Statistics counters
TOTAL_CHECKS=0
FAILED_CHECKS=0
SLOW_RESPONSES=0
HIGH_DB_CONN=0

# Trap Ctrl+C
trap 'echo -e "\n${CYAN}Monitoring stopped${NC}"; exit 0' INT TERM

# Main monitoring loop
while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - PREV_TIME))
    
    # Only calculate if enough time has passed
    if [ $ELAPSED -ge $INTERVAL ]; then
        TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
        
        # Clear previous output (keep header)
        tput cup 4 0
        tput ed
        
        echo -e "${BLUE}┌─ Network Status ────────────────────────────────────────────────┐${NC}"
        
        # Get current network stats
        CURRENT_STATS=$(get_network_stats "$NETWORK_IFACE")
        CURRENT_RX=$(echo "$CURRENT_STATS" | cut -d: -f1)
        CURRENT_TX=$(echo "$CURRENT_STATS" | cut -d: -f2)
        RX_PACKETS=$(echo "$CURRENT_STATS" | cut -d: -f3)
        TX_PACKETS=$(echo "$CURRENT_STATS" | cut -d: -f4)
        RX_ERRORS=$(echo "$CURRENT_STATS" | cut -d: -f5)
        TX_ERRORS=$(echo "$CURRENT_STATS" | cut -d: -f6)
        RX_DROPPED=$(echo "$CURRENT_STATS" | cut -d: -f7)
        TX_DROPPED=$(echo "$CURRENT_STATS" | cut -d: -f8)
        
        # Calculate throughput
        THROUGHPUT=$(calculate_throughput "$PREV_RX" "$PREV_TX" "$CURRENT_RX" "$CURRENT_TX" "$ELAPSED")
        RX_MBPS=$(echo "$THROUGHPUT" | cut -d: -f1)
        TX_MBPS=$(echo "$THROUGHPUT" | cut -d: -f2)
        
        # Display network stats
        printf "│ ${CYAN}Interface:${NC} %-50s │\n" "$NETWORK_IFACE"
        printf "│ ${CYAN}Throughput:${NC} RX: %6.2f Mbps  TX: %6.2f Mbps %14s │\n" "$RX_MBPS" "$TX_MBPS" ""
        printf "│ ${CYAN}Packets:${NC} RX: %10s  TX: %10s %20s │\n" "$RX_PACKETS" "$TX_PACKETS" ""
        
        # Check for errors
        if [ "$RX_ERRORS" -gt 0 ] || [ "$TX_ERRORS" -gt 0 ]; then
            printf "│ ${RED}Errors:${NC} RX: %10s  TX: %10s %20s │\n" "$RX_ERRORS" "$TX_ERRORS" ""
            alert WARN "Network errors detected: RX=$RX_ERRORS, TX=$TX_ERRORS"
        else
            printf "│ ${GREEN}Errors:${NC} RX: %10s  TX: %10s %20s │\n" "$RX_ERRORS" "$TX_ERRORS" ""
        fi
        
        # Check for drops
        if [ "$RX_DROPPED" -gt 10 ] || [ "$TX_DROPPED" -gt 10 ]; then
            printf "│ ${YELLOW}Dropped:${NC} RX: %10s  TX: %10s %19s │\n" "$RX_DROPPED" "$TX_DROPPED" ""
        else
            printf "│ ${GREEN}Dropped:${NC} RX: %10s  TX: %10s %19s │\n" "$RX_DROPPED" "$TX_DROPPED" ""
        fi
        
        echo -e "${BLUE}├─ API Health ───────────────────────────────────────────────────┤${NC}"
        
        # Check API health
        API_RESULT=$(check_api_health)
        API_STATUS=$(echo "$API_RESULT" | cut -d: -f1)
        API_TIME=$(echo "$API_RESULT" | cut -d: -f2 | cut -d. -f1)
        
        if [ "$API_STATUS" = "200" ]; then
            if [ "$API_TIME" -lt 100 ]; then
                printf "│ ${GREEN}Status:${NC} HTTP $API_STATUS  Response Time: %4d ms %19s │\n" "$API_TIME" "(Excellent)"
            elif [ "$API_TIME" -lt "$MAX_RESPONSE_TIME" ]; then
                printf "│ ${GREEN}Status:${NC} HTTP $API_STATUS  Response Time: %4d ms %22s │\n" "$API_TIME" "(Good)"
            else
                printf "│ ${YELLOW}Status:${NC} HTTP $API_STATUS  Response Time: %4d ms %23s │\n" "$API_TIME" "(Slow)"
                SLOW_RESPONSES=$((SLOW_RESPONSES + 1))
                alert WARN "Slow API response: ${API_TIME}ms"
            fi
        else
            printf "│ ${RED}Status:${NC} HTTP $API_STATUS  Response Time: %4d ms %20s │\n" "$API_TIME" "(Failed)"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            alert ERROR "API health check failed: HTTP $API_STATUS"
        fi
        
        echo -e "${BLUE}├─ Database ─────────────────────────────────────────────────────┤${NC}"
        
        # Get DB connections
        DB_CONN=$(get_db_connections)
        DB_USAGE_PCT=$((DB_CONN * 100 / 200))  # max_connections = 200
        
        if [ "$DB_CONN" -ge "$MAX_DB_CONNECTIONS" ]; then
            printf "│ ${RED}Connections:${NC} %3d / 200 (%3d%%) %30s │\n" "$DB_CONN" "$DB_USAGE_PCT" "(Critical)"
            HIGH_DB_CONN=$((HIGH_DB_CONN + 1))
            alert ERROR "High DB connection count: $DB_CONN"
        elif [ "$DB_CONN" -ge 150 ]; then
            printf "│ ${YELLOW}Connections:${NC} %3d / 200 (%3d%%) %31s │\n" "$DB_CONN" "$DB_USAGE_PCT" "(Warning)"
        else
            printf "│ ${GREEN}Connections:${NC} %3d / 200 (%3d%%) %33s │\n" "$DB_CONN" "$DB_USAGE_PCT" "(OK)"
        fi
        
        echo -e "${BLUE}├─ Container Health ─────────────────────────────────────────────┤${NC}"
        
        # Check key containers
        for container in mt5_db mt5_api mt5_pgbouncer mt5_prometheus; do
            HEALTH_RESULT=$(check_container_health "$container")
            CONT_STATUS=$(echo "$HEALTH_RESULT" | cut -d: -f1)
            CONT_HEALTH=$(echo "$HEALTH_RESULT" | cut -d: -f2)
            CONT_IP=$(get_container_ip "$container")
            
            if [ "$CONT_STATUS" = "running" ]; then
                if [ "$CONT_HEALTH" = "healthy" ] || [ "$CONT_HEALTH" = "N/A" ]; then
                    printf "│ ${GREEN}%-20s${NC} %-15s %-25s │\n" "$container" "$CONT_IP" "✓ Running"
                else
                    printf "│ ${YELLOW}%-20s${NC} %-15s %-25s │\n" "$container" "$CONT_IP" "⚠ $CONT_HEALTH"
                    alert WARN "Container $container is $CONT_HEALTH"
                fi
            else
                printf "│ ${RED}%-20s${NC} %-15s %-25s │\n" "$container" "N/A" "✗ $CONT_STATUS"
                alert ERROR "Container $container is $CONT_STATUS"
            fi
        done
        
        echo -e "${BLUE}├─ Statistics ───────────────────────────────────────────────────┤${NC}"
        
        # Calculate error rates
        if [ $TOTAL_CHECKS -gt 0 ]; then
            FAILED_PCT=$((FAILED_CHECKS * 100 / TOTAL_CHECKS))
            SUCCESS_PCT=$((100 - FAILED_PCT))
        else
            FAILED_PCT=0
            SUCCESS_PCT=100
        fi
        
        printf "│ Total Checks: %-10d Failed: %-10d Slow: %-10d │\n" "$TOTAL_CHECKS" "$FAILED_CHECKS" "$SLOW_RESPONSES"
        
        if [ "$SUCCESS_PCT" -ge "$MIN_SUCCESS_RATE" ]; then
            printf "│ ${GREEN}Success Rate: %3d%%${NC} %46s │\n" "$SUCCESS_PCT" ""
        else
            printf "│ ${RED}Success Rate: %3d%%${NC} %46s │\n" "$SUCCESS_PCT" ""
            alert ERROR "Low success rate: ${SUCCESS_PCT}%"
        fi
        
        echo -e "${BLUE}└─────────────────────────────────────────────────────────────────┘${NC}"
        
        echo ""
        echo -e "${CYAN}Last update: $(date +'%Y-%m-%d %H:%M:%S')${NC}"
        
        # Update previous values
        PREV_RX=$CURRENT_RX
        PREV_TX=$CURRENT_TX
        PREV_TIME=$CURRENT_TIME
    fi
    
    # Sleep for a short time
    sleep 1
done
