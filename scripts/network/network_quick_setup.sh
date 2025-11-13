#!/bin/bash
# MT5 Trading - Quick Network Setup
# Execute este script para configurar e validar a rede rapidamente

set -e

echo "🌐 MT5 Trading - Quick Network Setup"
echo "======================================"
echo ""

# Check if running as root for optimization
if [ "$EUID" -eq 0 ]; then
    IS_ROOT=true
else
    IS_ROOT=false
fi

# Step 1: Optimize system (requires root)
if [ "$IS_ROOT" = true ]; then
    echo "✓ Running as root - will optimize system"
    echo ""
    echo "Step 1/5: Optimizing system network settings..."
    ./optimize_network.sh
    echo ""
else
    echo "⚠ Not running as root - skipping system optimization"
    echo "  Run 'sudo ./network_quick_setup.sh' to optimize system"
    echo ""
fi

# Step 2: Check if containers are running
echo "Step 2/5: Checking Docker containers..."
RUNNING_CONTAINERS=$(docker ps --filter "name=mt5_" --format "{{.Names}}" | wc -l)

if [ "$RUNNING_CONTAINERS" -eq 0 ]; then
    echo "⚠ No MT5 containers running"
    echo ""
    read -p "Do you want to start the containers now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Starting containers..."
        docker compose up -d
        echo "Waiting 60s for containers to initialize..."
        sleep 60
    else
        echo "Skipping container startup"
        echo "Run 'docker compose up -d' manually when ready"
    fi
else
    echo "✓ Found $RUNNING_CONTAINERS MT5 containers running"
fi
echo ""

# Step 3: Run health check
echo "Step 3/5: Running network health check..."
./network_health_check.sh
HEALTH_STATUS=$?
echo ""

if [ $HEALTH_STATUS -eq 0 ]; then
    echo "✓ Health check passed!"
else
    echo "⚠ Health check found issues - review output above"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi
echo ""

# Step 4: Optional load test
echo "Step 4/5: Load testing (optional)..."
read -p "Do you want to run a quick load test (1 min, 50 req/s)? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running load test..."
    ./network_load_test.sh 60 50
    echo ""
else
    echo "Skipping load test"
    echo "You can run it later with: ./network_load_test.sh"
fi
echo ""

# Step 5: Setup monitoring
echo "Step 5/5: Monitoring setup..."
echo ""
echo "You can monitor the network in real-time with:"
echo "  ./network_monitor.sh"
echo ""
read -p "Do you want to start the monitor now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting network monitor..."
    echo "Press Ctrl+C to stop"
    sleep 2
    ./network_monitor.sh
else
    echo "You can start the monitor later with: ./network_monitor.sh"
fi
echo ""

# Final summary
echo "======================================"
echo "✓ Network setup completed!"
echo "======================================"
echo ""
echo "📚 Documentation:"
echo "  - NETWORK_OPTIMIZATION_GUIDE.md - Technical details"
echo "  - NETWORK_TOOLS_README.md - Script usage"
echo "  - NETWORK_OPTIMIZATION_SUMMARY.md - Executive summary"
echo ""
echo "🔧 Tools available:"
echo "  - ./network_health_check.sh - Health check"
echo "  - ./network_load_test.sh - Load testing"
echo "  - ./network_monitor.sh - Real-time monitoring"
echo "  - sudo ./optimize_network.sh - System optimization"
echo ""
echo "📊 Monitoring:"
echo "  - Grafana: http://localhost:13000"
echo "  - Prometheus: http://localhost:19090"
echo "  - API Docs: http://localhost:18003/docs"
echo ""
echo "Happy trading! 🚀"
