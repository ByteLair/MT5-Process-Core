#!/usr/bin/env bash
set -euo pipefail

# Installer for systemd service + timer
UNIT_DIR="/etc/systemd/system"
REPO_DIR="/home/felipe/MT5-Process-Core-full"

copy_unit() {
  local src="$1" dst="$2"
  if [[ ! -f "$src" ]]; then
    echo "Source unit not found: $src" >&2
    exit 1
  fi
  sudo cp -f "$src" "$dst"
}

main() {
  copy_unit "$REPO_DIR/systemd/mt5-maintenance.service" "$UNIT_DIR/mt5-maintenance.service"
  copy_unit "$REPO_DIR/systemd/mt5-maintenance.timer" "$UNIT_DIR/mt5-maintenance.timer"

  sudo systemctl daemon-reload

  # Enable on boot and start timer
  sudo systemctl enable mt5-maintenance.service || true
  sudo systemctl enable --now mt5-maintenance.timer

  echo "Installed systemd units:"
  systemctl list-timers | grep mt5-maintenance || true
}

main "$@"
