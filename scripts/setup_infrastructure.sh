#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Configuring MT5 Trading DB infrastructure...${NC}"

# 1. Security and Network
echo -e "\n${GREEN}1. Configuring firewall and SSH...${NC}"
sudo ufw allow 22
sudo ufw allow 8001
sudo ufw deny 5432
sudo ufw --force enable

sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/;s/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# 2. Docker Configuration
echo -e "\n${GREEN}2. Configuring Docker...${NC}"
sudo mkdir -p /etc/docker
sudo cp docker/daemon.json /etc/docker/daemon.json
sudo systemctl restart docker

# Setup cron for Docker cleanup
(crontab -l 2>/dev/null; echo "0 3 * * * docker system prune -af >/var/log/docker-prune.log 2>&1") | crontab -

# 3. Systemd Service
echo -e "\n${GREEN}3. Installing systemd service...${NC}"
sudo cp systemd/mt5-compose.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mt5-compose

# 4. Backup Configuration
echo -e "\n${GREEN}4. Setting up backup system...${NC}"
sudo mkdir -p /var/backups/mt5
sudo cp scripts/pg_backup.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/pg_backup.sh
(crontab -l 2>/dev/null; echo "30 2 * * * /usr/local/bin/pg_backup.sh >/var/log/pg_backup.log 2>&1") | crontab -

# 5. TimescaleDB Maintenance
echo -e "\n${GREEN}5. Configuring database maintenance...${NC}"
(crontab -l 2>/dev/null; echo "15 4 * * 0 docker exec -i mt5_db psql -U trader -d mt5_trading -c 'VACUUM (ANALYZE);'") | crontab -

# 6. Time Synchronization
echo -e "\n${GREEN}6. Setting up time synchronization...${NC}"
sudo apt install -y chrony
sudo systemctl enable --now chrony

# 7. Log Rotation
echo -e "\n${GREEN}7. Configuring log rotation...${NC}"
sudo mkdir -p /var/log/mt5
sudo cp logrotate.d/mt5 /etc/logrotate.d/
sudo chown root:root /etc/logrotate.d/mt5
sudo chmod 644 /etc/logrotate.d/mt5

# 8. Environment File Security
echo -e "\n${GREEN}8. Securing environment file...${NC}"
chmod 600 .env

# 9. Final Validation
echo -e "\n${GREEN}9. Validating setup...${NC}"
sudo ufw status
sudo systemctl status mt5-compose
docker ps
sudo systemctl list-timers | grep backup

echo -e "\n${GREEN}Setup completed successfully!${NC}
Please check the README.md for detailed documentation on the infrastructure setup."