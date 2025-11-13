#!/bin/bash
set -euo pipefail

# MT5 Trading - System Network Optimization Script
# Optimizes Linux kernel parameters for high-performance networking

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}This script must be run as root (use sudo)${NC}"
    exit 1
fi

echo "=========================================="
echo "🚀 MT5 Trading - Network Optimization"
echo "=========================================="
echo ""

# Backup current settings
BACKUP_FILE="/etc/sysctl.d/99-mt5-network.conf.backup.$(date +%Y%m%d_%H%M%S)"
if [ -f /etc/sysctl.d/99-mt5-network.conf ]; then
    cp /etc/sysctl.d/99-mt5-network.conf "$BACKUP_FILE"
    echo -e "${GREEN}✓${NC} Backed up existing configuration to $BACKUP_FILE"
fi

# Create optimized sysctl configuration
cat > /etc/sysctl.d/99-mt5-network.conf << 'EOF'
# MT5 Trading Platform - Network Optimization
# Generated on: $(date)

# ============================================================
# TCP/IP Stack Tuning
# ============================================================

# Increase max TCP buffer sizes (16MB)
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# Increase Linux autotuning TCP buffer limits
# min, default, and max number of bytes to use
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# Increase number of incoming connections backlog
net.core.netdev_max_backlog = 5000

# Increase socket listen backlog
net.core.somaxconn = 1024

# Increase number of incoming connections
net.ipv4.tcp_max_syn_backlog = 4096

# ============================================================
# TCP Performance Tuning
# ============================================================

# Enable TCP window scaling for high-bandwidth networks
net.ipv4.tcp_window_scaling = 1

# Enable TCP timestamps
net.ipv4.tcp_timestamps = 1

# Enable selective acknowledgements
net.ipv4.tcp_sack = 1

# Disable SYN cookies (can cause issues with legitimate traffic)
net.ipv4.tcp_syncookies = 1

# Enable TCP Fast Open for faster connection establishment
net.ipv4.tcp_fastopen = 3

# ============================================================
# Connection Reuse and Recycling
# ============================================================

# Allow reuse of TIME-WAIT sockets for new connections
net.ipv4.tcp_tw_reuse = 1

# Decrease TIME-WAIT timeout (default 60s)
net.ipv4.tcp_fin_timeout = 30

# Increase local port range
net.ipv4.ip_local_port_range = 10000 65535

# Increase max number of orphaned sockets
net.ipv4.tcp_max_orphans = 65536

# ============================================================
# Keepalive Settings
# ============================================================

# Time before sending keepalive probes (seconds)
net.ipv4.tcp_keepalive_time = 600

# Interval between keepalive probes (seconds)
net.ipv4.tcp_keepalive_intvl = 10

# Number of keepalive probes
net.ipv4.tcp_keepalive_probes = 5

# ============================================================
# Connection Tracking
# ============================================================

# Increase connection tracking table size
net.netfilter.nf_conntrack_max = 262144

# Timeout for established connections (seconds)
net.netfilter.nf_conntrack_tcp_timeout_established = 432000

# ============================================================
# Docker-Specific Optimizations
# ============================================================

# Enable IP forwarding (required for Docker)
net.ipv4.ip_forward = 1

# Enable bridge netfilter
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1

# ============================================================
# Memory and File Descriptors
# ============================================================

# Increase max number of open files
fs.file-max = 2097152

# Increase inotify watchers (for file monitoring)
fs.inotify.max_user_watches = 524288

# Virtual memory tuning for database workloads
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# ============================================================
# Performance and Latency
# ============================================================

# Disable IPv6 if not used (reduces overhead)
# net.ipv6.conf.all.disable_ipv6 = 1
# net.ipv6.conf.default.disable_ipv6 = 1

# TCP congestion control (cubic is default, bbr is better for high-bandwidth)
net.ipv4.tcp_congestion_control = cubic

# Enable ECN (Explicit Congestion Notification)
net.ipv4.tcp_ecn = 0

# Disable source routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# ============================================================
# Security Hardening
# ============================================================

# Protect against SYN flood attacks
net.ipv4.tcp_synack_retries = 2
net.ipv4.tcp_syn_retries = 2

# Disable ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0

# Disable send redirects
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Enable reverse path filtering
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Log martian packets
net.ipv4.conf.all.log_martians = 0

EOF

echo -e "${GREEN}✓${NC} Created optimized sysctl configuration"

# Apply settings
echo ""
echo "Applying network optimizations..."
sysctl -p /etc/sysctl.d/99-mt5-network.conf

echo ""
echo "=========================================="
echo "📋 Optimization Summary"
echo "=========================================="
echo ""
echo "Applied optimizations:"
echo "  ✓ TCP buffer sizes increased to 16MB"
echo "  ✓ Connection backlog increased to 5000"
echo "  ✓ Socket listen backlog increased to 1024"
echo "  ✓ TCP window scaling enabled"
echo "  ✓ TCP Fast Open enabled"
echo "  ✓ TIME-WAIT reuse enabled"
echo "  ✓ FIN timeout reduced to 30s"
echo "  ✓ Local port range expanded"
echo "  ✓ Keepalive optimized (600s, 10s interval)"
echo "  ✓ Connection tracking increased"
echo "  ✓ File descriptors increased"
echo "  ✓ Memory tuned for database workloads"
echo ""

# Set system-wide limits
echo "Configuring system limits..."
cat > /etc/security/limits.d/99-mt5-limits.conf << 'EOF'
# MT5 Trading Platform - System Limits

# Increase max number of open files
*       soft    nofile  65536
*       hard    nofile  1048576

# Increase max number of processes
*       soft    nproc   32768
*       hard    nproc   32768

# Increase max locked memory (for high-performance apps)
*       soft    memlock unlimited
*       hard    memlock unlimited

# Increase max stack size
*       soft    stack   8192
*       hard    stack   unlimited
EOF

echo -e "${GREEN}✓${NC} Updated system limits"

# Optimize Docker daemon
DOCKER_DAEMON_JSON="/etc/docker/daemon.json"
if [ -f "$DOCKER_DAEMON_JSON" ]; then
    cp "$DOCKER_DAEMON_JSON" "${DOCKER_DAEMON_JSON}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✓${NC} Backed up Docker daemon.json"
fi

# Create or update Docker daemon configuration
cat > "$DOCKER_DAEMON_JSON" << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  },
  "storage-driver": "overlay2",
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 1048576,
      "Soft": 65536
    },
    "nproc": {
      "Name": "nproc",
      "Hard": 32768,
      "Soft": 16384
    }
  },
  "default-shm-size": "256M",
  "userland-proxy": false,
  "icc": true,
  "live-restore": true,
  "bridge": "br-mt5"
}
EOF

echo -e "${GREEN}✓${NC} Optimized Docker daemon configuration"

# Reload Docker if it's running
if systemctl is-active --quiet docker; then
    echo ""
    echo "Restarting Docker daemon to apply changes..."
    systemctl restart docker
    echo -e "${GREEN}✓${NC} Docker daemon restarted"
fi

# Show current network settings
echo ""
echo "=========================================="
echo "📊 Current Network Settings"
echo "=========================================="
echo ""
echo "TCP Buffer Sizes:"
echo "  rmem_max: $(sysctl -n net.core.rmem_max)"
echo "  wmem_max: $(sysctl -n net.core.wmem_max)"
echo ""
echo "Connection Limits:"
echo "  max_backlog: $(sysctl -n net.core.netdev_max_backlog)"
echo "  somaxconn: $(sysctl -n net.core.somaxconn)"
echo "  max_syn_backlog: $(sysctl -n net.ipv4.tcp_max_syn_backlog)"
echo ""
echo "TCP Settings:"
echo "  window_scaling: $(sysctl -n net.ipv4.tcp_window_scaling)"
echo "  tcp_fastopen: $(sysctl -n net.ipv4.tcp_fastopen)"
echo "  tw_reuse: $(sysctl -n net.ipv4.tcp_tw_reuse)"
echo "  fin_timeout: $(sysctl -n net.ipv4.tcp_fin_timeout)"
echo ""
echo "Keepalive:"
echo "  time: $(sysctl -n net.ipv4.tcp_keepalive_time)s"
echo "  interval: $(sysctl -n net.ipv4.tcp_keepalive_intvl)s"
echo "  probes: $(sysctl -n net.ipv4.tcp_keepalive_probes)"
echo ""
echo "File Limits:"
echo "  file-max: $(sysctl -n fs.file-max)"
echo "  ulimit -n: $(ulimit -n)"
echo ""

# Recommendations
echo "=========================================="
echo "📝 Next Steps"
echo "=========================================="
echo ""
echo "1. Test the optimizations:"
echo "   ./network_health_check.sh"
echo ""
echo "2. Run load tests:"
echo "   ./network_load_test.sh 300 100"
echo ""
echo "3. Monitor in real-time:"
echo "   ./network_monitor.sh"
echo ""
echo "4. Restart affected services:"
echo "   docker compose restart"
echo ""
echo "5. Verify changes persist after reboot:"
echo "   sudo reboot"
echo "   sysctl -a | grep net.ipv4.tcp"
echo ""

echo -e "${GREEN}✓ Network optimization completed successfully!${NC}"
echo ""
echo "Configuration files:"
echo "  - /etc/sysctl.d/99-mt5-network.conf"
echo "  - /etc/security/limits.d/99-mt5-limits.conf"
echo "  - /etc/docker/daemon.json"
echo ""
echo "Backups saved with timestamp suffix."
