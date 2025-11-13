#!/bin/bash
###############################################################################
# K8s Logs Viewer for MT5 Trading Platform
# Usage: ./k8s-logs.sh [dev|staging|production] [component]
###############################################################################

ENVIRONMENT=${1:-dev}
COMPONENT=${2:-mt5-api}

# Colors
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get namespace
NAMESPACE="mt5-trading"
if [ "$ENVIRONMENT" == "dev" ]; then
    NAMESPACE="mt5-trading-dev"
elif [ "$ENVIRONMENT" == "staging" ]; then
    NAMESPACE="mt5-trading-staging"
fi

echo -e "${BLUE}[INFO]${NC} Viewing logs for $COMPONENT in $ENVIRONMENT environment..."
echo ""

kubectl logs -n "$NAMESPACE" -l "app=$COMPONENT" --tail=100 -f --prefix
