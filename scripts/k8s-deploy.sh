#!/bin/bash
###############################################################################
# K8s Deployment Script for MT5 Trading Platform
# Usage: ./deploy.sh [dev|staging|production]
###############################################################################

set -e

ENVIRONMENT=${1:-dev}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}/../k8s"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT"
    log_info "Usage: $0 [dev|staging|production]"
    exit 1
fi

log_info "🚀 Starting deployment to $ENVIRONMENT environment..."

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    log_error "kubectl not found. Please install kubectl first."
    exit 1
fi

if ! command -v kustomize &> /dev/null; then
    log_error "kustomize not found. Please install kustomize first."
    exit 1
fi

log_success "Prerequisites checked ✓"

# Build Docker images
log_info "Building Docker images..."

cd "${SCRIPT_DIR}/.."

# Build API image
log_info "Building API image..."
docker build -t mt5-trading-api:latest -f api/Dockerfile ./api

# Build ML image
log_info "Building ML image..."
docker build -t mt5-trading-ml:latest -f ml/Dockerfile ./ml

log_success "Docker images built ✓"

# Create namespace if it doesn't exist
NAMESPACE="mt5-trading"
if [ "$ENVIRONMENT" == "dev" ]; then
    NAMESPACE="mt5-trading-dev"
elif [ "$ENVIRONMENT" == "staging" ]; then
    NAMESPACE="mt5-trading-staging"
fi

log_info "Creating namespace: $NAMESPACE..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Apply Kustomize configuration
log_info "Applying Kustomize configuration for $ENVIRONMENT..."
kustomize build "${K8S_DIR}/overlays/${ENVIRONMENT}" | kubectl apply -f -

# Wait for deployments
log_info "Waiting for deployments to be ready..."

DEPLOYMENTS=(
    "postgres"
    "mt5-api"
    "ml-trainer"
    "prometheus"
    "grafana"
)

for deployment in "${DEPLOYMENTS[@]}"; do
    log_info "Waiting for $deployment..."
    kubectl rollout status deployment/"$deployment" -n "$NAMESPACE" --timeout=300s || {
        log_error "Deployment $deployment failed!"
        kubectl logs -n "$NAMESPACE" -l "app=$deployment" --tail=50
        exit 1
    }
done

log_success "All deployments ready ✓"

# Display service URLs
log_info "📊 Service Information:"
echo ""

kubectl get services -n "$NAMESPACE" -o wide

echo ""
log_info "🔗 Access URLs:"

API_URL=$(kubectl get service mt5-api-service -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
GRAFANA_URL=$(kubectl get service grafana-service -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")

echo -e "  ${GREEN}API:${NC} http://${API_URL}"
echo -e "  ${GREEN}API Docs:${NC} http://${API_URL}/docs"
echo -e "  ${GREEN}Grafana:${NC} http://${GRAFANA_URL}:3000"
echo -e "  ${GREEN}Prometheus:${NC} kubectl port-forward -n $NAMESPACE svc/prometheus-service 9090:9090"

echo ""
log_info "📝 Useful commands:"
echo "  kubectl get pods -n $NAMESPACE"
echo "  kubectl logs -n $NAMESPACE -l app=mt5-api --tail=100 -f"
echo "  kubectl describe pod -n $NAMESPACE <pod-name>"
echo "  kubectl exec -it -n $NAMESPACE <pod-name> -- /bin/bash"

echo ""
log_success "🎉 Deployment to $ENVIRONMENT completed successfully!"
