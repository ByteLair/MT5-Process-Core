# 🏗️ MT5 Trading Infrastructure - Terraform

## 📋 Overview

This directory contains Terraform configuration to provision the complete MT5 Trading infrastructure using Docker containers.

## 🎯 What's Provisioned

### Containers

- **PostgreSQL/TimescaleDB** - Time-series database for market data
- **API (FastAPI)** - REST API for data ingestion and signals
- **Prometheus** - Metrics collection and monitoring
- **Grafana** - Dashboards and visualization
- **ML Scheduler** - Machine learning model training scheduler

### Networks

- `mt5_network` - Bridge network for container communication

### Volumes

- `mt5_postgres_data` - Persistent PostgreSQL data
- `mt5_grafana_data` - Grafana configuration and dashboards
- `mt5_prometheus_data` - Prometheus metrics storage
- `mt5_models` - ML models storage

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install Terraform (if not installed)
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
terraform --version

# Install Docker (if not installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### Initialize Terraform

```bash
cd terraform
terraform init
```

### Plan (Preview Changes)

```bash
terraform plan
```

### Apply (Create Infrastructure)

```bash
terraform apply
```

### Destroy (Remove All Resources)

```bash
terraform destroy
```

---

## ⚙️ Configuration

### Variables

Edit `variables.tf` or create a `terraform.tfvars` file:

```hcl
postgres_user     = "trader"
postgres_password = "your_secure_password"
postgres_db       = "mt5_trading"
api_port          = 18001
api_key           = "your_api_key_here"
grafana_admin_user     = "admin"
grafana_admin_password = "your_grafana_password"
```

### Environment Variables

Alternatively, use environment variables:

```bash
export TF_VAR_postgres_password="your_secure_password"
export TF_VAR_api_key="your_api_key_here"
export TF_VAR_grafana_admin_password="your_grafana_password"
```

---

## 📊 Access URLs

After applying Terraform, access services at:

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | `http://localhost:18001` | API Key (X-API-Key header) |
| **API Health** | `http://localhost:18001/health` | - |
| **API Docs** | `http://localhost:18001/docs` | - |
| **Prometheus** | `http://localhost:9090` | - |
| **Grafana** | `http://localhost:3000` | admin / admin (default) |

### View Outputs

```bash
terraform output
```

### View Sensitive Outputs

```bash
terraform output -json | jq
```

---

## 🔍 Verification

### Check Container Status

```bash
docker ps --filter "name=mt5_"
```

### Check Logs

```bash
docker logs mt5_api
docker logs mt5_db
docker logs mt5_grafana
docker logs mt5_prometheus
```

### Test API

```bash
# Health check
curl http://localhost:18001/health

# Send test data
curl -X POST "http://localhost:18001/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{"ts":"2025-10-18T14:00:00Z","symbol":"EURUSD","timeframe":"M1","open":1.0950,"high":1.0955,"low":1.0948,"close":1.0952,"volume":1250}'
```

### Query Database

```bash
docker exec -it mt5_db psql -U trader -d mt5_trading -c "SELECT COUNT(*) FROM market_data;"
```

---

## 📈 Grafana Dashboard

### Automatic Provisioning

The Grafana dashboard is automatically provisioned on startup:

- **Dashboard Name**: MT5 Trading - Main Dashboard
- **Location**: `grafana/provisioning/dashboards/mt5-trading-main.json`

### Dashboard Features

1. **Total Candles Inserted** - Real-time counter
2. **API Status** - UP/DOWN indicator
3. **Total Records** - Database size
4. **Active Symbols** - Number of trading pairs
5. **Ingestion Rate** - Candles per second
6. **Records per Minute** - Time series chart
7. **Last Data Received** - Table with latest timestamps
8. **Data Distribution** - Pie chart by symbol
9. **Price Chart** - Major pairs (EURUSD, GBPUSD, USDJPY)
10. **Latest Market Data** - Table with last 50 records

### Manual Dashboard Import

If needed, import manually:

1. Go to Grafana → Dashboards → Import
2. Upload `grafana/provisioning/dashboards/mt5-trading-main.json`

---

## 🔐 Security Best Practices

### 1. Change Default Passwords

```bash
# Generate secure passwords
openssl rand -base64 32

# Update terraform.tfvars
cat > terraform.tfvars <<EOF
postgres_password      = "$(openssl rand -base64 32)"
api_key                = "$(openssl rand -base64 32)"
grafana_admin_password = "$(openssl rand -base64 32)"
EOF
```

### 2. Use Secrets Management

For production, use:

- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Environment variables from CI/CD

### 3. Network Security

```bash
# Restrict access to specific IPs
iptables -A INPUT -p tcp --dport 18001 -s YOUR_IP -j ACCEPT
iptables -A INPUT -p tcp --dport 18001 -j DROP
```

---

## 🛠️ Troubleshooting

### Issue: "Error creating container"

**Solution:** Check if ports are already in use

```bash
sudo lsof -i :18001
sudo lsof -i :3000
sudo lsof -i :9090
```

### Issue: "Unable to connect to Docker daemon"

**Solution:** Start Docker service

```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### Issue: Database initialization failed

**Solution:** Remove volume and recreate

```bash
terraform destroy -target=docker_volume.postgres_data
terraform apply
```

### Issue: Grafana dashboard not loading

**Solution:** Check provisioning directory permissions

```bash
chmod -R 755 ../grafana/provisioning
terraform apply -replace=docker_container.grafana
```

---

## 📁 File Structure

```
terraform/
├── main.tf           # Main Terraform configuration
├── variables.tf      # Input variables
├── outputs.tf        # Output values
├── terraform.tfvars  # Variable values (gitignored)
└── README.md         # This file

grafana/
├── provisioning/
│   ├── datasources/
│   │   └── datasources.yml
│   └── dashboards/
│       ├── dashboards.yml
│       └── mt5-trading-main.json
```

---

## 🔄 Updates and Maintenance

### Update Container Images

```bash
# Pull latest images
docker pull timescale/timescaledb:2.14.2-pg16
docker pull prom/prometheus:v2.52.0
docker pull grafana/grafana-oss:11.0.0

# Recreate containers
terraform apply -replace=docker_container.postgres
terraform apply -replace=docker_container.prometheus
terraform apply -replace=docker_container.grafana
```

### Rebuild Custom Images

```bash
# Rebuild API image
cd ../api
docker build -t mt5-api:latest .
cd ../terraform
terraform apply -replace=docker_container.api

# Rebuild ML image
cd ../ml
docker build -t mt5-ml:latest .
cd ../terraform
terraform apply -replace=docker_container.ml_scheduler
```

### Backup Data

```bash
# Backup PostgreSQL
docker exec mt5_db pg_dump -U trader mt5_trading > backup_$(date +%Y%m%d).sql

# Backup Grafana
docker cp mt5_grafana:/var/lib/grafana grafana_backup_$(date +%Y%m%d)

# Backup Prometheus
docker cp mt5_prometheus:/prometheus prometheus_backup_$(date +%Y%m%d)
```

---

## 🧪 Testing

### Test Complete Stack

```bash
# Apply infrastructure
terraform apply -auto-approve

# Wait for services to be ready
sleep 30

# Test health endpoints
curl http://localhost:18001/health
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health

# Send test data
curl -X POST "http://localhost:18001/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod" \
  -d '{"ts":"2025-10-18T14:00:00Z","symbol":"EURUSD","timeframe":"M1","open":1.0950,"high":1.0955,"low":1.0948,"close":1.0952,"volume":1250}'

# Verify in database
docker exec mt5_db psql -U trader -d mt5_trading -c "SELECT * FROM market_data ORDER BY ts DESC LIMIT 5;"

# Check metrics
curl http://localhost:18001/metrics

# Verify Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check Grafana datasources
curl -u admin:admin http://localhost:3000/api/datasources
```

---

## 📚 Additional Resources

- [Terraform Docker Provider](https://registry.terraform.io/providers/kreuzwerker/docker/latest/docs)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## 🤝 Contributing

1. Make changes to Terraform files
2. Run `terraform fmt` to format code
3. Run `terraform validate` to check syntax
4. Test with `terraform plan`
5. Apply with `terraform apply`

---

**Version:** 1.0
**Last Updated:** 2025-10-18
**Status:** ✅ Production Ready
