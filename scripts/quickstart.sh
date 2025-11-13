#!/bin/bash
set -e

echo "=========================================="
echo "🚀 MT5 Trading - Quick Start"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Starting services with Docker Compose...${NC}"
docker compose up -d

echo ""
echo -e "${BLUE}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# Check API health
echo -e "${BLUE}🔍 Checking API health...${NC}"
if curl -s http://localhost:18001/health | grep -q "ok"; then
    echo -e "${GREEN}✅ API is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  API is not ready yet, wait a few more seconds${NC}"
fi

# Check Prometheus
echo -e "${BLUE}🔍 Checking Prometheus...${NC}"
if curl -s http://localhost:9090/-/healthy | grep -q "Prometheus"; then
    echo -e "${GREEN}✅ Prometheus is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Prometheus is not ready yet${NC}"
fi

# Check Grafana
echo -e "${BLUE}🔍 Checking Grafana...${NC}"
if curl -s http://localhost:3000/api/health | grep -q "ok"; then
    echo -e "${GREEN}✅ Grafana is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Grafana is not ready yet${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ MT5 Trading is now running!${NC}"
echo "=========================================="
echo ""
echo -e "${BLUE}📊 Access URLs:${NC}"
echo -e "  • API:        http://localhost:18001"
echo -e "  • API Docs:   http://localhost:18001/docs"
echo -e "  • API Health: http://localhost:18001/health"
echo -e "  • Prometheus: http://localhost:9090"
echo -e "  • Grafana:    http://localhost:3000 ${YELLOW}(admin/admin)${NC}"
echo -e "  • pgAdmin:    http://localhost:5051"
echo ""
echo -e "${BLUE}📈 Grafana Dashboard:${NC}"
echo -e "  • Go to: http://localhost:3000"
echo -e "  • Login: admin / admin"
echo -e "  • Dashboard: 'MT5 Trading - Main Dashboard'"
echo ""
echo -e "${BLUE}🧪 Test API:${NC}"
echo -e "  curl http://localhost:18001/health"
echo ""
echo -e "  curl -X POST 'http://localhost:18001/ingest' \\"
echo -e "    -H 'Content-Type: application/json' \\"
echo -e "    -H 'X-API-Key: mt5_trading_secure_key_2025_prod' \\"
echo -e "    -d '{\"ts\":\"2025-10-18T14:00:00Z\",\"symbol\":\"EURUSD\",\"timeframe\":\"M1\",\"open\":1.0950,\"high\":1.0955,\"low\":1.0948,\"close\":1.0952,\"volume\":1250}'"
echo ""
echo -e "${BLUE}📊 View Logs:${NC}"
echo -e "  docker compose logs -f api"
echo -e "  docker compose logs -f db"
echo ""
echo -e "${BLUE}🛑 Stop Services:${NC}"
echo -e "  docker compose down"
echo ""
echo "=========================================="
