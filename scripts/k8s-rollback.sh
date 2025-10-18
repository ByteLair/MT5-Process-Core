#!/bin/bash
###############################################################################
# K8s Rollback Script for MT5 Trading Platform
# Usage: ./k8s-rollback.sh [dev|staging|production] [deployment-name]
###############################################################################

set -e

ENVIRONMENT=${1:-dev}
DEPLOYMENT=${2:-mt5-api}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    log_info "Usage: $0 [dev|staging|production] [deployment-name]"
    exit 1
fi

# Get namespace
NAMESPACE="mt5-trading"
if [ "$ENVIRONMENT" == "dev" ]; then
    NAMESPACE="mt5-trading-dev"
elif [ "$ENVIRONMENT" == "staging" ]; then
    NAMESPACE="mt5-trading-staging"
fi

log_info "🔄 Rolling back $DEPLOYMENT in $ENVIRONMENT environment..."

# Show rollout history
log_info "Rollout history:"
kubectl rollout history deployment/"$DEPLOYMENT" -n "$NAMESPACE"

# Perform rollback
log_info "Performing rollback..."
kubectl rollout undo deployment/"$DEPLOYMENT" -n "$NAMESPACE"

# Wait for rollback to complete
log_info "Waiting for rollback to complete..."
kubectl rollout status deployment/"$DEPLOYMENT" -n "$NAMESPACE" --timeout=300s

log_success "✅ Rollback completed successfully!"

# Show current pods
log_info "Current pods:"
kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT"
