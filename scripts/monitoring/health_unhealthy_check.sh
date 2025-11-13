#!/usr/bin/env bash
# Check for containers with unhealthy health status and report/exit non-zero if any found
set -euo pipefail

UNHEALTHY=$(docker ps --format '{{.Names}} {{.Status}}' --filter "health=unhealthy" -q)
if [ -n "$UNHEALTHY" ]; then
  echo "Unhealthy containers found:"
  docker ps --filter "health=unhealthy"
  exit 2
fi
exit 0
