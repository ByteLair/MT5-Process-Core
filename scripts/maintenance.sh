#!/usr/bin/env bash
set -euo pipefail

# Enhanced maintenance script for mt5-trading-db
# Features:
# - Ensure stack is up (db, pgbouncer, api, prometheus, grafana, loki, promtail, jaeger)
# - Restart unhealthy containers
# - Clear port conflicts (docker-proxy) for common ports
# - Wait for key endpoints (API metrics, Prometheus, Loki, Jaeger)
# - Subcommands: up | restart-unhealthy | clear-ports | check | full | prune

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILES=("-f" "$PROJECT_DIR/docker-compose.yml")
if [[ -f "$PROJECT_DIR/docker-compose.override.yml" ]]; then
  COMPOSE_FILES+=("-f" "$PROJECT_DIR/docker-compose.override.yml")
fi

SERVICES=(db pgbouncer api prometheus grafana loki promtail jaeger node-exporter)
CONFLICT_PORTS=(4317 4318 3100 9090 3000 18003 9100)

PROM_URL="http://127.0.0.1:19090"
API_METRICS_URL="http://127.0.0.1:18003/prometheus/"
API_HEALTH_URL="http://127.0.0.1:18003/health"
JAEGER_URL="http://127.0.0.1:16686"
LOKI_URL="http://127.0.0.1:3100"
GRAFANA_URL="http://127.0.0.1:3000"

log() { echo "[$(date '+%F %T')] $*"; }

ensure_up() {
  log "Ensuring services are up: ${SERVICES[*]}"
  docker compose "${COMPOSE_FILES[@]}" up -d ${SERVICES[*]}
}

restart_unhealthy() {
  log "Checking for unhealthy containers"
  local unhealthy
  unhealthy=$(docker ps --filter "health=unhealthy" --format '{{.Names}}') || true
  if [[ -n "$unhealthy" ]]; then
    log "Restarting unhealthy: $unhealthy"
    docker restart $unhealthy || true
  else
    log "No unhealthy containers"
  fi
}

clear_port_conflicts() {
  log "Clearing port conflicts if any: ${CONFLICT_PORTS[*]}"
  for p in "${CONFLICT_PORTS[@]}"; do
    # Skip if sudo not available without TTY
    if ! sudo -n true 2>/dev/null; then
      log "sudo not available non-interactively; skipping kill on port $p"
      continue
    fi
    pids=$(sudo netstat -tlnp 2>/dev/null \
      | awk -v pat=":$p$" '$4 ~ pat {print $7}' \
      | cut -d/ -f1 \
      | sort -u \
      | tr '\n' ' ' || true)
    if [[ -n "$pids" ]]; then
      log "Killing docker-proxy on port $p: $pids"
      sudo kill -9 $pids || true
    fi
  done
}

wait_http() {
  local url="$1" name="$2" timeout="${3:-30}"
  log "Waiting for $name at $url (timeout=${timeout}s)"
  local start=$(date +%s)
  while true; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "$name is ready"
      return 0
    fi
    local now=$(date +%s)
    if (( now - start > timeout )); then
      log "Timeout waiting for $name"
      return 1
    fi
    sleep 2
  done
}

check_observability() {
  # API health & metrics
  wait_http "$API_HEALTH_URL" "API health" 60 || true
  wait_http "$API_METRICS_URL" "API metrics" 60 || true

  # Prometheus targets
  if wait_http "$PROM_URL/-/ready" "Prometheus" 60; then
    log "Prometheus scrape status (sum by job of up):"
    curl -s --get --data-urlencode 'query=sum by(job)(up)' "$PROM_URL/api/v1/query" | jq -r '.data.result[] | "job=\(.metric.job) up=\(.value[1])"' || true
    log "mt5-api up:"
    curl -s --get --data-urlencode 'query=up{job="mt5-api"}' "$PROM_URL/api/v1/query" | jq -r '.data.result[0].value[1] // "N/A"' || true
    log "node-exporter up:"
    curl -s --get --data-urlencode 'query=up{job="node-exporter"}' "$PROM_URL/api/v1/query" | jq -r '.data.result[0].value[1] // "N/A"' || true
  fi

  # Loki readiness
  wait_http "$LOKI_URL/ready" "Loki ready" 60 || true

  # Jaeger UI
  wait_http "$JAEGER_URL" "Jaeger UI" 60 || true

  # Grafana (no auth): check login page
  wait_http "$GRAFANA_URL/login" "Grafana login" 60 || true
}

status() {
  log "Containers status:"
  docker ps --format '{{.Names}}\t{{.Status}}' | sort || true
}

prune_unused() {
  log "Pruning unused images/containers/networks..."
  docker system prune -f || true
}

usage() {
  cat <<EOF
Usage: $(basename "$0") [subcommand]

Subcommands:
  up                 Ensure stack is up
  restart-unhealthy  Restart containers with health=unhealthy
  clear-ports        Kill docker-proxy on common ports
  check              Wait and check core endpoints
  full               clear-ports -> up -> restart-unhealthy -> check
  prune              docker system prune -f

No subcommand defaults to: full
EOF
}

main() {
  local cmd="${1:-full}"
  case "$cmd" in
    up)
      ensure_up ;;
    restart-unhealthy)
      restart_unhealthy ;;
    clear-ports)
      clear_port_conflicts ;;
    check)
      check_observability ; status ;;
    prune)
      prune_unused ;;
    full)
      clear_port_conflicts
      ensure_up
      restart_unhealthy
      check_observability ; status ;;
    *)
      usage ; exit 1 ;;
  esac
}

main "$@"
