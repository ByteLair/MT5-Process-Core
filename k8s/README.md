# ☸️ Kubernetes Configuration

Configuração completa de Kubernetes para a plataforma MT5 Trading.

---

## 📁 Estrutura

```
k8s/
├── base/                          # Configuração base (11 manifests)
│   ├── namespace.yaml             # Namespace mt5-trading
│   ├── configmap.yaml             # App configs + SQL init
│   ├── secrets.yaml               # Credentials template
│   ├── persistent-volumes.yaml    # 4 PVs/PVCs (37Gi total)
│   ├── postgres-deployment.yaml   # TimescaleDB + Service
│   ├── api-deployment.yaml        # FastAPI + Service + HPA
│   ├── ml-deployment.yaml         # ML Trainer + CronJob
│   ├── prometheus-deployment.yaml # Prometheus + RBAC
│   ├── grafana-deployment.yaml    # Grafana + Datasources
│   ├── ingress.yaml               # NGINX Ingress + TLS
│   └── kustomization.yaml         # Base kustomization
│
└── overlays/                      # Environment-specific configs
    ├── dev/
    │   └── kustomization.yaml     # Dev overrides
    ├── staging/
    │   └── kustomization.yaml     # Staging overrides
    └── production/
        └── kustomization.yaml     # Production overrides
```

---

## 🚀 Quick Deploy

### Development
```bash
kubectl apply -k overlays/dev
```

### Staging
```bash
kubectl apply -k overlays/staging
```

### Production
```bash
# 1. Update secrets first!
kubectl create secret generic mt5-trading-secrets \
  -n mt5-trading \
  --from-literal=POSTGRES_PASSWORD='prod_password' \
  --from-literal=API_KEY='prod_key' \
  --from-literal=GF_SECURITY_ADMIN_PASSWORD='prod_grafana' \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Deploy
kubectl apply -k overlays/production

# 3. Verify
kubectl get all -n mt5-trading
```

---

## 📊 Resources

### Deployments (5)
- **postgres** - TimescaleDB database
- **mt5-api** - FastAPI backend (2-10 replicas with HPA)
- **ml-trainer** - ML model training
- **prometheus** - Metrics collection
- **grafana** - Monitoring dashboards

### Services (4)
- **postgres-service** - ClusterIP:5432
- **mt5-api-service** - LoadBalancer:80
- **prometheus-service** - ClusterIP:9090
- **grafana-service** - LoadBalancer:3000

### Storage (4 PVCs)
- **postgres-pvc** - 20Gi (Database)
- **ml-models-pvc** - 5Gi (ML Models, RWX)
- **grafana-pvc** - 2Gi (Dashboards)
- **prometheus-pvc** - 10Gi (Metrics)

### Autoscaling (1 HPA)
- **mt5-api-hpa** - Scale API 2-10 replicas based on CPU/Memory

### Jobs (1 CronJob)
- **ml-training-job** - Daily at 2 AM

### Networking (1 Ingress)
- api.mt5-trading.local
- grafana.mt5-trading.local
- prometheus.mt5-trading.local

---

## 🎯 Environment Differences

| Feature | Dev | Staging | Production |
|---------|-----|---------|------------|
| **API Replicas** | 1 | 2 | 3 |
| **HPA Min** | 1 | 2 | 3 |
| **HPA Max** | 3 | 5 | 10 |
| **Log Level** | DEBUG | INFO | WARNING |
| **Workers** | 2 | 3 | 4 |
| **Namespace** | mt5-trading-dev | mt5-trading-staging | mt5-trading |

---

## 🔧 Customization

### Update Replicas
Edit `overlays/{env}/kustomization.yaml`:
```yaml
patches:
  - patch: |-
      apiVersion: apps/v1
      kind: Deployment
      metadata:
        name: mt5-api
      spec:
        replicas: 5
    target:
      kind: Deployment
      name: mt5-api
```

### Update Resources
Edit deployment files in `base/`:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### Update ConfigMap
Edit `base/configmap.yaml`:
```yaml
data:
  LOG_LEVEL: "INFO"
  WORKERS: "4"
```

---

## 📚 Documentation

Complete guides:
- [K8S Deployment Guide](../docs/K8S_DEPLOYMENT.md)
- [Quick Reference](../docs/K8S_QUICK_REFERENCE.md)
- [Implementation Summary](../docs/K8S_IMPLEMENTATION_SUMMARY.md)

---

## 🛠️ Scripts

Use helper scripts from `scripts/`:
```bash
# Deploy
../scripts/k8s-deploy.sh [dev|staging|production]

# Health check
../scripts/k8s-healthcheck.sh [env]

# Scale
../scripts/k8s-scale.sh [env] [deployment] [replicas]

# Rollback
../scripts/k8s-rollback.sh [env] [deployment]

# Logs
../scripts/k8s-logs.sh [env] [component]
```

---

## 🔐 Security Notes

1. **Never commit real secrets** to git
2. Use external secrets management (Vault, AWS Secrets Manager)
3. Update passwords in production
4. Enable RBAC (already configured)
5. Use NetworkPolicies for pod isolation
6. Enable TLS for Ingress

---

## 📈 Monitoring

After deployment, access:
```bash
# Grafana (port-forward)
kubectl port-forward -n mt5-trading svc/grafana-service 3000:3000
# http://localhost:3000 (admin/admin)

# Prometheus
kubectl port-forward -n mt5-trading svc/prometheus-service 9090:9090
# http://localhost:9090

# API
kubectl port-forward -n mt5-trading svc/mt5-api-service 8000:80
# http://localhost:8000/docs
```

---

## 🔍 Troubleshooting

### Pods not starting
```bash
kubectl get pods -n mt5-trading
kubectl describe pod <pod-name> -n mt5-trading
kubectl logs <pod-name> -n mt5-trading
```

### PVC Pending
```bash
kubectl get pvc -n mt5-trading
kubectl describe pvc <pvc-name> -n mt5-trading
```

### Service not accessible
```bash
kubectl get svc -n mt5-trading
kubectl get endpoints -n mt5-trading
```

See full troubleshooting guide in [K8S_DEPLOYMENT.md](../docs/K8S_DEPLOYMENT.md).

---

## 🎓 Best Practices

✅ Use Kustomize overlays for environments  
✅ Keep secrets out of git  
✅ Set resource limits  
✅ Use health checks  
✅ Enable RBAC  
✅ Use namespaces for isolation  
✅ Tag images with versions  
✅ Use StatefulSets for stateful apps  
✅ Implement NetworkPolicies  
✅ Monitor everything  

---

**Version**: 2.0.0  
**Last Updated**: 18/10/2025
