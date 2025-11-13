#!/bin/bash
# Health Check System - Complete monitoring for containers and pipelines
# Stores logs in SQLite database and generates daily reports

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs/health-checks"
DB_FILE="$LOG_DIR/health_checks.db"
ALERT_THRESHOLD=3  # Number of consecutive failures before alert

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$LOG_DIR"

# Initialize database
init_database() {
    sqlite3 "$DB_FILE" <<EOF
CREATE TABLE IF NOT EXISTS health_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    check_type TEXT NOT NULL,
    component_name TEXT NOT NULL,
    status TEXT NOT NULL,
    details TEXT,
    response_time_ms INTEGER,
    cpu_usage REAL,
    memory_usage REAL,
    disk_usage REAL
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    component_name TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    message TEXT,
    resolved BOOLEAN DEFAULT 0,
    resolved_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_timestamp ON health_checks(timestamp);
CREATE INDEX IF NOT EXISTS idx_component ON health_checks(component_name);
CREATE INDEX IF NOT EXISTS idx_status ON health_checks(status);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved);
EOF
}

# Get container stats
get_container_stats() {
    local container_name=$1
    local stats=$(docker stats "$container_name" --no-stream --format "{{.CPUPerc}}|{{.MemUsage}}" 2>/dev/null || echo "0%|0B / 0B")

    local cpu=$(echo "$stats" | cut -d'|' -f1 | sed 's/%//')
    local mem=$(echo "$stats" | cut -d'|' -f2 | awk '{print $1}' | numfmt --from=iec 2>/dev/null || echo "0")
    local mem_total=$(echo "$stats" | cut -d'|' -f2 | awk '{print $3}' | numfmt --from=iec 2>/dev/null || echo "1")
    local mem_percent=$(awk "BEGIN {printf \"%.2f\", ($mem/$mem_total)*100}")

    echo "$cpu|$mem_percent"
}

# Check Docker containers
check_containers() {
    echo -e "${BLUE}🐳 Checking Docker Containers...${NC}"

    local containers=("mt5_db" "mt5_api" "mt5_prometheus" "mt5_grafana" "mt5_pgadmin")

    for container in "${containers[@]}"; do
        local start_time=$(date +%s%3N)

        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            local end_time=$(date +%s%3N)
            local response_time=$((end_time - start_time))

            # Get container health
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
            if [ "$health" = "none" ]; then
                health="running"
            fi

            # Get stats
            local stats=$(get_container_stats "$container")
            local cpu=$(echo "$stats" | cut -d'|' -f1)
            local mem=$(echo "$stats" | cut -d'|' -f2)

            if [ "$health" = "healthy" ] || [ "$health" = "running" ]; then
                echo -e "${GREEN}✓${NC} $container: $health (CPU: ${cpu}%, MEM: ${mem}%)"
                log_check "container" "$container" "healthy" "$health" "$response_time" "$cpu" "$mem"
            else
                echo -e "${RED}✗${NC} $container: $health"
                log_check "container" "$container" "unhealthy" "$health" "$response_time" "$cpu" "$mem"
                check_alert "$container" "unhealthy"
            fi
        else
            echo -e "${RED}✗${NC} $container: not running"
            log_check "container" "$container" "down" "container not found" 0 0 0
            check_alert "$container" "down"
        fi
    done
}

# Check API endpoints
check_api_endpoints() {
    echo -e "\n${BLUE}🌐 Checking API Endpoints...${NC}"

    local endpoints=(
        "http://localhost:8001/health|API Health"
        "http://localhost:8001/docs|API Docs"
        "http://localhost:9090/-/healthy|Prometheus"
        "http://localhost:3000/api/health|Grafana"
    )

    for endpoint_info in "${endpoints[@]}"; do
        local url=$(echo "$endpoint_info" | cut -d'|' -f1)
        local name=$(echo "$endpoint_info" | cut -d'|' -f2)

        local start_time=$(date +%s%3N)
        local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
        local end_time=$(date +%s%3N)
        local response_time=$((end_time - start_time))

        if [ "$response" = "200" ]; then
            echo -e "${GREEN}✓${NC} $name: OK (${response_time}ms)"
            log_check "api" "$name" "healthy" "HTTP $response" "$response_time"
        else
            echo -e "${RED}✗${NC} $name: FAILED (HTTP $response)"
            log_check "api" "$name" "unhealthy" "HTTP $response" "$response_time"
            check_alert "$name" "api_down"
        fi
    done
}

# Check database
check_database() {
    echo -e "\n${BLUE}🗄️  Checking Database...${NC}"

    local start_time=$(date +%s%3N)
    local result=$(docker exec mt5_db psql -U trader -d mt5_trading -c "SELECT 1;" 2>&1)
    local end_time=$(date +%s%3N)
    local response_time=$((end_time - start_time))

    if echo "$result" | grep -q "1 row"; then
        echo -e "${GREEN}✓${NC} Database: Connected (${response_time}ms)"

        # Get DB size
        local db_size=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT pg_size_pretty(pg_database_size('mt5_trading'));" 2>/dev/null | xargs)

        # Get table count
        local table_count=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT COUNT(*) FROM market_data;" 2>/dev/null | xargs)

        echo -e "  ${BLUE}├─${NC} Size: $db_size"
        echo -e "  ${BLUE}└─${NC} Records: $table_count"

        log_check "database" "PostgreSQL" "healthy" "size: $db_size, records: $table_count" "$response_time"
    else
        echo -e "${RED}✗${NC} Database: Connection failed"
        log_check "database" "PostgreSQL" "unhealthy" "$result" "$response_time"
        check_alert "PostgreSQL" "db_connection_failed"
    fi
}

# Check disk space
check_disk_space() {
    echo -e "\n${BLUE}💾 Checking Disk Space...${NC}"

    local usage=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $5}' | sed 's/%//')
    local available=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $4}')

    if [ "$usage" -lt 80 ]; then
        echo -e "${GREEN}✓${NC} Disk Space: ${usage}% used (${available} available)"
        log_check "system" "Disk Space" "healthy" "${usage}% used, ${available} free" 0 0 0 "$usage"
    elif [ "$usage" -lt 90 ]; then
        echo -e "${YELLOW}⚠${NC} Disk Space: ${usage}% used (${available} available)"
        log_check "system" "Disk Space" "warning" "${usage}% used, ${available} free" 0 0 0 "$usage"
    else
        echo -e "${RED}✗${NC} Disk Space: ${usage}% used (${available} available)"
        log_check "system" "Disk Space" "critical" "${usage}% used, ${available} free" 0 0 0 "$usage"
        check_alert "Disk Space" "disk_full"
    fi
}

# Check GitHub Actions runner
check_runner() {
    echo -e "\n${BLUE}🤖 Checking GitHub Actions Runner...${NC}"

    local runner_status=$(systemctl is-active actions.runner.Lysk-dot-mt5-trading-db.2v4g1.service 2>/dev/null || echo "inactive")

    if [ "$runner_status" = "active" ]; then
        echo -e "${GREEN}✓${NC} GitHub Runner: Active"
        log_check "cicd" "GitHub Runner" "healthy" "systemd service active" 0
    else
        echo -e "${RED}✗${NC} GitHub Runner: $runner_status"
        log_check "cicd" "GitHub Runner" "unhealthy" "systemd service $runner_status" 0
        check_alert "GitHub Runner" "runner_down"
    fi
}

# Log check to database
log_check() {
    local check_type=$1
    local component=$2
    local status=$3
    local details=$4
    local response_time=${5:-0}
    local cpu=${6:-0}
    local mem=${7:-0}
    local disk=${8:-0}

    sqlite3 "$DB_FILE" <<EOF
INSERT INTO health_checks (check_type, component_name, status, details, response_time_ms, cpu_usage, memory_usage, disk_usage)
VALUES ('$check_type', '$component', '$status', '$details', $response_time, $cpu, $mem, $disk);
EOF
}

# Check for repeated failures and create alerts
check_alert() {
    local component=$1
    local alert_type=$2

    # Count recent failures (last 5 minutes)
    local failure_count=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM health_checks WHERE component_name='$component' AND status IN ('unhealthy', 'down', 'critical') AND timestamp > datetime('now', '-5 minutes');")

    if [ "$failure_count" -ge "$ALERT_THRESHOLD" ]; then
        # Check if alert already exists
        local existing_alert=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM alerts WHERE component_name='$component' AND resolved=0;")

        if [ "$existing_alert" -eq 0 ]; then
            local message="Component $component has failed $failure_count times in the last 5 minutes"
            sqlite3 "$DB_FILE" "INSERT INTO alerts (component_name, alert_type, message) VALUES ('$component', '$alert_type', '$message');"
            echo -e "${RED}🚨 ALERT: $message${NC}"
        fi
    fi
}

# Generate daily report
generate_daily_report() {
    local today=$(date +%Y-%m-%d)
    local report_file="$LOG_DIR/daily_report_$today.txt"

    cat > "$report_file" <<EOF
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║          📊 HEALTH CHECK DAILY REPORT - $today            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

Generated: $(date '+%Y-%m-%d %H:%M:%S')

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Checks: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM health_checks WHERE DATE(timestamp)='$today';")
Healthy: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM health_checks WHERE DATE(timestamp)='$today' AND status='healthy';")
Unhealthy: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM health_checks WHERE DATE(timestamp)='$today' AND status IN ('unhealthy', 'down', 'critical');")
Warnings: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM health_checks WHERE DATE(timestamp)='$today' AND status='warning';")

Alerts Created: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM alerts WHERE DATE(timestamp)='$today';")
Alerts Resolved: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM alerts WHERE DATE(timestamp)='$today' AND resolved=1;")
Alerts Pending: $(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM alerts WHERE DATE(timestamp)='$today' AND resolved=0;")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🐳 CONTAINER STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

$(sqlite3 "$DB_FILE" "SELECT component_name, COUNT(*) as checks,
    SUM(CASE WHEN status='healthy' THEN 1 ELSE 0 END) as healthy,
    ROUND(AVG(cpu_usage), 2) as avg_cpu,
    ROUND(AVG(memory_usage), 2) as avg_mem,
    ROUND(AVG(response_time_ms), 0) as avg_response
FROM health_checks
WHERE DATE(timestamp)='$today' AND check_type='container'
GROUP BY component_name;" | awk -F'|' '{printf "%-20s Checks: %3d | Healthy: %3d | CPU: %5.2f%% | MEM: %5.2f%% | Response: %4dms\n", $1, $2, $3, $4, $5, $6}')

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 API ENDPOINTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

$(sqlite3 "$DB_FILE" "SELECT component_name, COUNT(*) as checks,
    SUM(CASE WHEN status='healthy' THEN 1 ELSE 0 END) as healthy,
    ROUND(AVG(response_time_ms), 0) as avg_response,
    MIN(response_time_ms) as min_response,
    MAX(response_time_ms) as max_response
FROM health_checks
WHERE DATE(timestamp)='$today' AND check_type='api'
GROUP BY component_name;" | awk -F'|' '{printf "%-20s Checks: %3d | Healthy: %3d | Avg: %4dms | Min: %4dms | Max: %4dms\n", $1, $2, $3, $4, $5, $6}')

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🗄️  DATABASE PERFORMANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

$(sqlite3 "$DB_FILE" "SELECT
    COUNT(*) as checks,
    SUM(CASE WHEN status='healthy' THEN 1 ELSE 0 END) as healthy,
    ROUND(AVG(response_time_ms), 0) as avg_response,
    MIN(response_time_ms) as min_response,
    MAX(response_time_ms) as max_response
FROM health_checks
WHERE DATE(timestamp)='$today' AND check_type='database';" | awk -F'|' '{printf "Checks: %d | Healthy: %d | Avg: %dms | Min: %dms | Max: %dms\n", $1, $2, $3, $4, $5}')

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 ALERTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

$(sqlite3 "$DB_FILE" "SELECT timestamp, component_name, alert_type, message FROM alerts WHERE DATE(timestamp)='$today' ORDER BY timestamp DESC;" | awk -F'|' '{printf "%s | %-20s | %-20s | %s\n", $1, $2, $3, $4}')

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 RECENT FAILURES (Last 10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

$(sqlite3 "$DB_FILE" "SELECT timestamp, check_type, component_name, status, details FROM health_checks WHERE DATE(timestamp)='$today' AND status IN ('unhealthy', 'down', 'critical') ORDER BY timestamp DESC LIMIT 10;" | awk -F'|' '{printf "%s | %-10s | %-20s | %-10s | %s\n", $1, $2, $3, $4, $5}')

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Report saved to: $report_file
EOF

    cat "$report_file"
}

# Main execution
main() {
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                               ║${NC}"
    echo -e "${BLUE}║            🏥 HEALTH CHECK SYSTEM - $(date +%H:%M:%S)                  ║${NC}"
    echo -e "${BLUE}║                                                               ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Initialize database
    init_database

    # Run all checks
    check_containers
    check_api_endpoints
    check_database
    check_disk_space
    check_runner

    echo ""
    echo -e "${GREEN}✅ Health check completed!${NC}"
    echo -e "${BLUE}📊 Database: $DB_FILE${NC}"
    echo -e "${BLUE}📁 Logs: $LOG_DIR${NC}"
}

# Run main function
if [ "${1:-}" = "--report" ]; then
    generate_daily_report
else
    main
fi
