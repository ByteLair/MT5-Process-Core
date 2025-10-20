#!/usr/bin/env bash
set -euo pipefail

# Restart Docker daemon with pre/post checks to clear orphaned docker-proxy bindings.
# Usage: sudo ./restart-docker.sh [--yes] [--health-url http://localhost:18001/health]

HEALTH_URL=${HEALTH_URL:-http://localhost:18001/health}
ASSUME_YES=${1:-}

echo "== Pre-checks: docker and port status =="
ss -ltnp | grep -E ':8001\b' || true
lsof -nP -iTCP:8001 -sTCP:LISTEN || true

echo "\nDocker containers (summary):"
docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}'

if [[ "$ASSUME_YES" != "--yes" ]]; then
  read -rp "Proceed to restart Docker daemon? This will momentarily interrupt containers. [y/N] " yn
  case "$yn" in
    [Yy]*) : ;;
    *) echo "Aborted by user."; exit 1;;
  esac
fi

echo "\n== Restarting Docker service =="
if sudo systemctl restart docker; then
  echo "systemctl restart docker OK"
else
  echo "systemctl restart docker failed; trying snap.docker.dockerd restart"
  sudo systemctl restart snap.docker.dockerd
fi

# Wait for docker to become ready
echo "Waiting for docker to be active..."
for i in {1..30}; do
  if sudo systemctl is-active --quiet docker; then
    echo "docker active"
    break
  fi
  sleep 1
done

# Post-checks
echo "\n== Post-checks: port and containers =="
ss -ltnp | grep -E ':8001\b' || echo 'no binding on 8001'
lsof -nP -iTCP:8001 -sTCP:LISTEN || true

docker ps --format 'table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}'

echo "\n== Optional: test health endpoint =="
if command -v curl >/dev/null 2>&1; then
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    echo "Health check ok: $HEALTH_URL"
  else
    echo "Health check failed: $HEALTH_URL"
    echo "Check container logs for details: docker logs <container> --tail 200"
  fi
else
  echo "curl not found; skipping health test"
fi

echo "\nMaintenance script finished. Review output above for issues."
