#!/bin/bash
# Quick setup for Health Check System

set -e

echo "🏥 Setting up Health Check System..."

# Install Flask for web dashboard
echo "📦 Installing Flask..."
if [ -d ".venv" ]; then
    source .venv/bin/activate
    pip install flask --quiet 2>/dev/null || true
else
    pip3 install flask --user --quiet 2>/dev/null || pip install flask --user --quiet 2>/dev/null || true
fi

# Make scripts executable
chmod +x scripts/health-check.sh
chmod +x scripts/health-dashboard.py

# Create log directory
mkdir -p logs/health-checks

# Run initial health check
echo "🔍 Running initial health check..."
./scripts/health-check.sh

echo ""
echo "✅ Health Check System installed successfully!"
echo ""
echo "📊 Quick Actions:"
echo "  • Run health check:    ./scripts/health-check.sh"
echo "  • Generate report:     ./scripts/health-check.sh --report"
echo "  • Start web dashboard: python3 scripts/health-dashboard.py"
echo "  • View database:       sqlite3 logs/health-checks/health_checks.db"
echo ""
echo "🌐 Dashboards:"
echo "  • Web Dashboard:  http://localhost:5001"
echo "  • Grafana:        http://localhost:3000/d/health-check-dash"
echo ""
echo "📁 Files:"
echo "  • Database:  logs/health-checks/health_checks.db"
echo "  • Reports:   logs/health-checks/daily_report_*.txt"
echo ""
