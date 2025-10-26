# ⎈ MT5 Trading Helm Chart

Helm chart oficial para deploy da plataforma MT5 Trading em Kubernetes.

---

## 📦 Chart Information

- **Chart Name**: mt5-trading
- **Chart Version**: 2.0.0
- **App Version**: 2.0.0
- **Type**: Application

---

## 🚀 Quick Start

### Install

```bash
# Basic install
helm install mt5-trading . -n mt5-trading --create-namespace

# With custom values
helm install mt5-trading . -n mt5-trading -f my-values.yaml

# Dry run (test)
helm install mt5-trading . -n mt5-trading --dry-run --debug
```

### Upgrade

```bash
helm upgrade mt5-trading . -n mt5-trading

# Force upgrade
helm upgrade --force mt5-trading . -n mt5-trading
```

### Uninstall

```bash
helm uninstall mt5-trading -n mt5-trading
```

---

## ⚙️ Configuration

### Common Values

Create `my-values.yaml`:

```yaml
# API Configuration
api:
  replicaCount: 3
  apiKey: "your-secure-api-key"

  resources:
    requests:
      memory: "512Mi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "2000m"

  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 15
    targetCPUUtilizationPercentage: 60

# PostgreSQL Configuration
postgres:
  auth:
    username: trader
    password: "your-secure-postgres-password"
    database: mt5_trading

  persistence:
    enabled: true
    size: 50Gi

# Grafana Configuration
grafana:
  auth:
    adminUser: admin
    adminPassword: "your-secure-grafana-password"

  persistence:
    enabled: true
    size: 5Gi

# ML Configuration
ml:
  enabled: true
  scheduler:
    schedule: "0 3 * * *"  # 3 AM daily
```

---

## 📊 Components

### Enabled by Default

- ✅ PostgreSQL/TimescaleDB
- ✅ FastAPI API
- ✅ ML Trainer
- ✅ ML Scheduler (CronJob)
- ✅ Prometheus
- ✅ Grafana
- ✅ HPA (HorizontalPodAutoscaler)
- ✅ Ingress (optional)

### Optional Components

Configure in `values.yaml`:

```yaml
# Disable components
ml:
  enabled: false

prometheus:
  enabled: false

grafana:
  enabled: false
```

---

## 🔐 Security

### Update Secrets

**Important**: Update default passwords before production!

```yaml
postgres:
  auth:
    password: "CHANGE-ME"

api:
  apiKey: "CHANGE-ME"

grafana:
  auth:
    adminPassword: "CHANGE-ME"
```

Or use existing secrets:

```bash
kubectl create secret generic mt5-trading-secrets \
  -n mt5-trading \
  --from-literal=POSTGRES_PASSWORD='prod_password' \
  --from-literal=API_KEY='prod_api_key' \
  --from-literal=GF_SECURITY_ADMIN_PASSWORD='prod_grafana'
```

---

## 🌐 Networking

### Ingress

Enable and configure:

```yaml
api:
  ingress:
    enabled: true
    className: nginx
    host: api.mt5-trading.example.com
    tls:
      enabled: true
      secretName: mt5-trading-tls

grafana:
  ingress:
    enabled: true
    className: nginx
    host: grafana.mt5-trading.example.com
    tls:
      enabled: true
      secretName: mt5-trading-tls

prometheus:
  ingress:
    enabled: true
    className: nginx
    host: prometheus.mt5-trading.example.com
    tls:
      enabled: true
      secretName: mt5-trading-tls
```

### Service Types

```yaml
# LoadBalancer (cloud)
api:
  service:
    type: LoadBalancer

# ClusterIP (internal only)
api:
  service:
    type: ClusterIP

# NodePort (expose on node)
api:
  service:
    type: NodePort
    nodePort: 30080
```

---

## 💾 Storage

### Persistence

```yaml
# Enable/disable persistence
postgres:
  persistence:
    enabled: true
    size: 50Gi
    storageClass: "standard"

ml:
  persistence:
    enabled: true
    size: 10Gi
    storageClass: "standard"

grafana:
  persistence:
    enabled: true
    size: 5Gi
    storageClass: "standard"

prometheus:
  persistence:
    enabled: true
    size: 20Gi
    storageClass: "standard"
```

---

## 📈 Autoscaling

### HPA Configuration

```yaml
api:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 20
    targetCPUUtilizationPercentage: 60
    targetMemoryUtilizationPercentage: 75
```

---

## 🔧 Advanced Configuration

### Resource Limits

```yaml
# Per component
postgres:
  resources:
    requests:
      memory: "1Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "4000m"

api:
  resources:
    requests:
      memory: "512Mi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "2000m"
```

### Environment-Specific

```yaml
# Development
config:
  logLevel: DEBUG
  workers: 2

api:
  replicaCount: 1
  autoscaling:
    minReplicas: 1
    maxReplicas: 3

# Production
config:
  logLevel: WARNING
  workers: 4

api:
  replicaCount: 3
  autoscaling:
    minReplicas: 3
    maxReplicas: 20
```

---

## 📚 Examples

### Minimal Production Deploy

```yaml
# minimal-prod.yaml
api:
  replicaCount: 3
  apiKey: "prod-secure-key-12345"

postgres:
  auth:
    password: "prod-postgres-secure-password"

grafana:
  auth:
    adminPassword: "prod-grafana-secure-password"
```

```bash
helm install mt5-trading . -n mt5-trading -f minimal-prod.yaml
```

### High Availability Setup

```yaml
# ha-setup.yaml
api:
  replicaCount: 5
  autoscaling:
    minReplicas: 5
    maxReplicas: 30
    targetCPUUtilizationPercentage: 50

  resources:
    requests:
      memory: "1Gi"
      cpu: "1000m"
    limits:
      memory: "4Gi"
      cpu: "4000m"

postgres:
  persistence:
    size: 100Gi
  resources:
    requests:
      memory: "2Gi"
      cpu: "2000m"
    limits:
      memory: "8Gi"
      cpu: "8000m"
```

### Development Setup

```yaml
# dev-setup.yaml
api:
  replicaCount: 1
  autoscaling:
    enabled: false

config:
  logLevel: DEBUG
  workers: 2

postgres:
  persistence:
    size: 10Gi
  resources:
    requests:
      memory: "512Mi"
      cpu: "500m"

# Disable monitoring in dev
prometheus:
  enabled: false
grafana:
  enabled: false
```

---

## 🛠️ Helm Commands

### List Releases

```bash
helm list -n mt5-trading
```

### Get Values

```bash
# Get deployed values
helm get values mt5-trading -n mt5-trading

# Get all values (including defaults)
helm get values mt5-trading -n mt5-trading --all
```

### Rollback

```bash
# Rollback to previous version
helm rollback mt5-trading -n mt5-trading

# Rollback to specific revision
helm rollback mt5-trading 2 -n mt5-trading
```

### History

```bash
helm history mt5-trading -n mt5-trading
```

### Test

```bash
helm test mt5-trading -n mt5-trading
```

---

## 🔍 Troubleshooting

### View Generated Manifests

```bash
helm template mt5-trading . -n mt5-trading > manifests.yaml
cat manifests.yaml
```

### Dry Run

```bash
helm install mt5-trading . -n mt5-trading --dry-run --debug
```

### Get Rendered Values

```bash
helm get manifest mt5-trading -n mt5-trading
```

### Common Issues

**Helm install fails**

```bash
# Check syntax
helm lint .

# Debug install
helm install mt5-trading . -n mt5-trading --dry-run --debug
```

**Release exists**

```bash
# Delete and reinstall
helm uninstall mt5-trading -n mt5-trading
helm install mt5-trading . -n mt5-trading
```

---

## 📋 Values Reference

See `values.yaml` for complete configuration options.

### Main Sections

```yaml
global:              # Global settings
postgres:            # PostgreSQL configuration
api:                 # API configuration
ml:                  # ML configuration
prometheus:          # Prometheus configuration
grafana:             # Grafana configuration
config:              # Application config
serviceAccount:      # ServiceAccount settings
rbac:                # RBAC settings
```

---

## 🎓 Best Practices

✅ Always use custom values file
✅ Never commit secrets to git
✅ Use `--dry-run` before production
✅ Pin chart versions
✅ Set resource limits
✅ Enable persistence in production
✅ Use external secrets management
✅ Test in staging first
✅ Document custom values
✅ Regular backups

---

## 📚 Documentation

- [Full K8s Guide](../../docs/K8S_DEPLOYMENT.md)
- [Quick Reference](../../docs/K8S_QUICK_REFERENCE.md)
- [Project Structure](../../docs/PROJECT_STRUCTURE.md)

---

## 🤝 Contributing

To contribute to this chart:

1. Make changes
2. Test with `helm lint .`
3. Test install with `--dry-run`
4. Update version in `Chart.yaml`
5. Document changes
6. Submit PR

---

## 📄 License

MIT License - See [LICENSE](../../LICENSE)

---

**Chart Version**: 2.0.0
**App Version**: 2.0.0
**Maintained by**: Felipe
**Last Updated**: 18/10/2025
