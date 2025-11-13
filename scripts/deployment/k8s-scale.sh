#!/bin/bash
###############################################################################
# K8s Scale Script for MT5 Trading Platform
# Usage: ./k8s-scale.sh [dev|staging|production] [deployment-name] [replicas]
###############################################################################

set -e

ENVIRONMENT=${1:-dev}
DEPLOYMENT=${2:-mt5-api}
REPLICAS=${3:-3}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    log_info "Usage: $0 [dev|staging|production] [deployment-name] [replicas]"
    exit 1
fi

# Get namespace
NAMESPACE="mt5-trading"
if [ "$ENVIRONMENT" == "dev" ]; then
    NAMESPACE="mt5-trading-dev"
elif [ "$ENVIRONMENT" == "staging" ]; then
    NAMESPACE="mt5-trading-staging"
fi

log_info "📊 Scaling $DEPLOYMENT to $REPLICAS replicas in $ENVIRONMENT environment..."

# Scale deployment
kubectl scale deployment/"$DEPLOYMENT" --replicas="$REPLICAS" -n "$NAMESPACE"

# Wait for scaling to complete
log_info "Waiting for scaling to complete..."
kubectl rollout status deployment/"$DEPLOYMENT" -n "$NAMESPACE" --timeout=300s

log_success "✅ Scaling completed successfully!"

# Show current pods
log_info "Current pods:"
kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT"
