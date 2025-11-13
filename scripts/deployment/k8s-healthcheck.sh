#!/bin/bash
###############################################################################
# K8s Health Check Script for MT5 Trading Platform
# Usage: ./k8s-healthcheck.sh [dev|staging|production]
###############################################################################

set -e

ENVIRONMENT=${1:-dev}

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
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    log_info "Usage: $0 [dev|staging|production]"
    exit 1
fi

# Get namespace
NAMESPACE="mt5-trading"
if [ "$ENVIRONMENT" == "dev" ]; then
    NAMESPACE="mt5-trading-dev"
elif [ "$ENVIRONMENT" == "staging" ]; then
    NAMESPACE="mt5-trading-staging"
fi

echo ""
echo "=================================================="
echo "   MT5 Trading K8s Health Check - $ENVIRONMENT"
echo "=================================================="
echo ""

# Check cluster connection
log_info "Checking cluster connection..."
if kubectl cluster-info &> /dev/null; then
    log_success "Connected to Kubernetes cluster"
else
    log_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

# Check namespace
log_info "Checking namespace: $NAMESPACE..."
if kubectl get namespace "$NAMESPACE" &> /dev/null; then
    log_success "Namespace exists"
else
    log_error "Namespace not found"
    exit 1
fi

# Check deployments
log_info "Checking deployments..."
DEPLOYMENTS=(
    "postgres"
    "mt5-api"
    "ml-trainer"
    "prometheus"
    "grafana"
)

ALL_HEALTHY=true

for deployment in "${DEPLOYMENTS[@]}"; do
    if kubectl get deployment "$deployment" -n "$NAMESPACE" &> /dev/null; then
        READY=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
        DESIRED=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.replicas}')

        if [ "$READY" == "$DESIRED" ]; then
            log_success "$deployment: $READY/$DESIRED pods ready"
        else
            log_error "$deployment: $READY/$DESIRED pods ready"
            ALL_HEALTHY=false
        fi
    else
        log_error "$deployment: not found"
        ALL_HEALTHY=false
    fi
done

# Check services
log_info "Checking services..."
SERVICES=(
    "postgres-service"
    "mt5-api-service"
    "prometheus-service"
    "grafana-service"
)

for service in "${SERVICES[@]}"; do
    if kubectl get service "$service" -n "$NAMESPACE" &> /dev/null; then
        CLUSTER_IP=$(kubectl get service "$service" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
        log_success "$service: $CLUSTER_IP"
    else
        log_error "$service: not found"
        ALL_HEALTHY=false
    fi
done

# Check persistent volumes
log_info "Checking persistent volumes..."
PVC_COUNT=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
PVC_BOUND=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null | grep -c "Bound" || echo "0")

if [ "$PVC_COUNT" -gt 0 ]; then
    if [ "$PVC_BOUND" == "$PVC_COUNT" ]; then
        log_success "All PVCs bound: $PVC_BOUND/$PVC_COUNT"
    else
        log_warning "Some PVCs not bound: $PVC_BOUND/$PVC_COUNT"
    fi
else
    log_warning "No PVCs found"
fi

# Check pods
log_info "Checking pod status..."
PODS_TOTAL=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
PODS_RUNNING=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null | grep -c "Running" || echo "0")

if [ "$PODS_RUNNING" == "$PODS_TOTAL" ]; then
    log_success "All pods running: $PODS_RUNNING/$PODS_TOTAL"
else
    log_error "Some pods not running: $PODS_RUNNING/$PODS_TOTAL"
    ALL_HEALTHY=false

    echo ""
    log_info "Non-running pods:"
    kubectl get pods -n "$NAMESPACE" | grep -v "Running" | tail -n +2
fi

# Check HPA
log_info "Checking HorizontalPodAutoscaler..."
if kubectl get hpa mt5-api-hpa -n "$NAMESPACE" &> /dev/null; then
    CURRENT=$(kubectl get hpa mt5-api-hpa -n "$NAMESPACE" -o jsonpath='{.status.currentReplicas}')
    DESIRED=$(kubectl get hpa mt5-api-hpa -n "$NAMESPACE" -o jsonpath='{.status.desiredReplicas}')
    log_success "HPA: $CURRENT/$DESIRED replicas"
else
    log_warning "HPA not found"
fi

# Check recent events
log_info "Recent events (last 5)..."
kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -n 6

echo ""
echo "=================================================="
if [ "$ALL_HEALTHY" = true ]; then
    log_success "✅ All systems healthy!"
    exit 0
else
    log_error "❌ Some systems are unhealthy!"
    exit 1
fi
