#!/bin/bash
set -e

# MT5 Trading - Complete Health Check Script
# Verifica a saúde de todos os componentes do sistema

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=========================================="
echo "🏥 MT5 Trading - Health Check"
echo "=========================================="
echo ""

# Function to check service
check_service() {
    local service_name=$1
    local url=$2
    local expected=$3
    
    echo -n "🔍 Checking $service_name... "
    
    if response=$(curl -s --max-time 5 "$url" 2>/dev/null); then
        if echo "$response" | grep -q "$expected"; then
            echo -e "${GREEN}✅ OK${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  Running but unexpected response${NC}"
            echo "   Response: $response"
            return 1
        fi
    else
        echo -e "${RED}❌ FAILED${NC}"
        return 1
    fi
}

# Check Docker
echo -e "${BLUE}📦 Docker Status:${NC}"
if docker info > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker is running${NC}"
else
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi
echo ""

# Check Containers
echo -e "${BLUE}🐳 Container Status:${NC}"
containers=("mt5_db" "mt5_api" "mt5_prometheus" "mt5_grafana")
all_running=true

for container in "${containers[@]}"; do
    echo -n "   $container: "
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        status=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null)
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
        
        if [ "$status" = "running" ]; then
            if [ "$health" = "healthy" ]; then
                echo -e "${GREEN}✅ Running (Healthy)${NC}"
            elif [ "$health" = "N/A" ]; then
                echo -e "${GREEN}✅ Running${NC}"
            else
                echo -e "${YELLOW}⚠️  Running ($health)${NC}"
                all_running=false
            fi
        else
            echo -e "${RED}❌ $status${NC}"
            all_running=false
        fi
    else
        echo -e "${RED}❌ Not running${NC}"
        all_running=false
    fi
done
echo ""

# Check API Health
echo -e "${BLUE}🌐 API Health:${NC}"
check_service "API Health" "http://localhost:18001/health" "ok"
check_service "API Docs" "http://localhost:18001/docs" "swagger"
echo ""

# Check Prometheus
echo -e "${BLUE}📊 Prometheus Health:${NC}"
check_service "Prometheus" "http://localhost:9090/-/healthy" "Prometheus"
echo ""

# Check Grafana
echo -e "${BLUE}📈 Grafana Health:${NC}"
check_service "Grafana" "http://localhost:3000/api/health" "ok"
echo ""

# Check Database
echo -e "${BLUE}🗄️  Database Health:${NC}"
if docker exec mt5_db pg_isready -U trader -d mt5_trading > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
    
    # Get database stats
    db_size=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT pg_size_pretty(pg_database_size('mt5_trading'));" 2>/dev/null | xargs)
    total_records=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT COUNT(*) FROM market_data;" 2>/dev/null | xargs)
    active_symbols=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT COUNT(DISTINCT symbol) FROM market_data;" 2>/dev/null | xargs)
    
    echo "   Database Size: $db_size"
    echo "   Total Records: $total_records"
    echo "   Active Symbols: $active_symbols"
else
    echo -e "${RED}❌ PostgreSQL is not ready${NC}"
fi
echo ""

# Check Metrics
echo -e "${BLUE}📉 Metrics Check:${NC}"
if metrics=$(curl -s http://localhost:18001/prometheus/ 2>/dev/null); then
    total_inserted=$(echo "$metrics" | grep "^ingest_candles_inserted_total" | awk '{print $2}')
    echo "   Total Candles Inserted: ${total_inserted:-0}"
    
    # Check if receiving data recently
    recent_data=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "SELECT COUNT(*) FROM market_data WHERE ts >= NOW() - INTERVAL '10 minutes';" 2>/dev/null | xargs)
    echo "   Data Last 10 Minutes: ${recent_data:-0}"
    
    if [ "${recent_data:-0}" -gt 0 ]; then
        echo -e "   ${GREEN}✅ Receiving data${NC}"
    else
        echo -e "   ${YELLOW}⚠️  No recent data${NC}"
    fi
else
    echo -e "${RED}❌ Cannot fetch metrics${NC}"
fi
echo ""

# Check Disk Space
echo -e "${BLUE}💾 Disk Space:${NC}"
disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
disk_avail=$(df -h / | awk 'NR==2 {print $4}')

echo -n "   Root Filesystem: "
if [ "$disk_usage" -lt 80 ]; then
    echo -e "${GREEN}${disk_usage}% used (${disk_avail} available)${NC}"
elif [ "$disk_usage" -lt 90 ]; then
    echo -e "${YELLOW}${disk_usage}% used (${disk_avail} available) - Warning${NC}"
else
    echo -e "${RED}${disk_usage}% used (${disk_avail} available) - Critical${NC}"
fi
echo ""

# Check Docker Volumes
echo -e "${BLUE}📦 Docker Volumes:${NC}"
volumes=("db_data" "grafana_data" "prometheus_data" "models_mt5")
for vol in "${volumes[@]}"; do
    if docker volume inspect "$vol" > /dev/null 2>&1; then
        vol_size=$(docker system df -v | grep "$vol" | awk '{print $3}' || echo "N/A")
        echo -e "   $vol: ${GREEN}✅${NC} ($vol_size)"
    else
        echo -e "   $vol: ${RED}❌ Not found${NC}"
    fi
done
echo ""

# Summary
echo "=========================================="
if $all_running; then
    echo -e "${GREEN}✅ All systems operational!${NC}"
else
    echo -e "${YELLOW}⚠️  Some issues detected${NC}"
fi
echo "=========================================="
echo ""

# Quick Actions
echo -e "${BLUE}🔧 Quick Actions:${NC}"
echo "   View logs:        docker compose logs -f [service]"
echo "   Restart service:  docker compose restart [service]"
echo "   Full restart:     docker compose restart"
echo "   Stop all:         docker compose down"
echo "   Start all:        docker compose up -d"
echo ""
