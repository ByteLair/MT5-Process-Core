# 🚀 Kubernetes Deployment Guide

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Pré-requisitos](#pré-requisitos)
- [Quick Start](#quick-start)
- [Deployment com Kustomize](#deployment-com-kustomize)
- [Deployment com Helm](#deployment-com-helm)
- [Gerenciamento](#gerenciamento)
- [Monitoramento](#monitoramento)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

Deploy completo da plataforma MT5 Trading em Kubernetes com:

✅ **Multi-ambiente** - Dev, Staging, Production
✅ **Auto-scaling** - HPA configurado para API
✅ **Persistent Storage** - PV/PVC para dados críticos
✅ **Health Checks** - Liveness e Readiness probes
✅ **Service Discovery** - ClusterIP e LoadBalancer
✅ **Ingress** - NGINX com TLS
✅ **RBAC** - Service Accounts e Roles configurados

---

## 📦 Pré-requisitos

### Ferramentas Necessárias

```bash
# Kubernetes CLI
kubectl version --client

# Kustomize
kustomize version

# Helm (opcional)
helm version

# Docker
docker --version
```

### Cluster Kubernetes

Você pode usar:

- **Minikube** (desenvolvimento local)
- **Kind** (Kubernetes in Docker)
- **K3s** (lightweight)
- **GKE, EKS, AKS** (cloud)

**Exemplo com Minikube:**

```bash
# Iniciar Minikube
minikube start --cpus=4 --memory=8192 --disk-size=20g

# Habilitar addons
minikube addons enable ingress
minikube addons enable metrics-server
```

---

## ⚡ Quick Start

### 1. Build das Imagens

```bash
cd /home/felipe/mt5-trading-db

# Build API
docker build -t mt5-trading-api:latest -f api/Dockerfile ./api

# Build ML
docker build -t mt5-trading-ml:latest -f ml/Dockerfile ./ml

# Se usando Minikube, carregar imagens
minikube image load mt5-trading-api:latest
minikube image load mt5-trading-ml:latest
```

### 2. Deploy Rápido (Dev)

```bash
# Usar script automatizado
./scripts/k8s-deploy.sh dev
```

### 3. Verificar Status

```bash
# Health check
./scripts/k8s-healthcheck.sh dev

# Ver pods
kubectl get pods -n mt5-trading-dev

# Ver services
kubectl get svc -n mt5-trading-dev
```

---

## 🔧 Deployment com Kustomize

### Estrutura

```
k8s/
├── base/                          # Configuração base
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── persistent-volumes.yaml
│   ├── postgres-deployment.yaml
│   ├── api-deployment.yaml
│   ├── ml-deployment.yaml
│   ├── prometheus-deployment.yaml
│   ├── grafana-deployment.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
└── overlays/                      # Overlays por ambiente
    ├── dev/
    │   └── kustomization.yaml
    ├── staging/
    │   └── kustomization.yaml
    └── production/
        └── kustomization.yaml
```

### Deploy por Ambiente

#### Development

```bash
# Preview
kustomize build k8s/overlays/dev

# Apply
kubectl apply -k k8s/overlays/dev

# Ou usar script
./scripts/k8s-deploy.sh dev
```

#### Staging

```bash
kubectl apply -k k8s/overlays/staging
# Ou
./scripts/k8s-deploy.sh staging
```

#### Production

```bash
# ⚠️ IMPORTANTE: Atualizar secrets primeiro!
kubectl create secret generic mt5-trading-secrets \
  -n mt5-trading \
  --from-literal=POSTGRES_PASSWORD='production_password' \
  --from-literal=API_KEY='production_api_key' \
  --from-literal=GF_SECURITY_ADMIN_PASSWORD='production_grafana_password' \
  --dry-run=client -o yaml | kubectl apply -f -

# Deploy
kubectl apply -k k8s/overlays/production
# Ou
./scripts/k8s-deploy.sh production
```

### Personalização de Overlays

Edite `k8s/overlays/{env}/kustomization.yaml`:

```yaml
# Exemplo: Alterar número de réplicas
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

---

## 📊 Deployment com Helm

### Instalação

```bash
cd helm/mt5-trading

# Install
helm install mt5-trading . -n mt5-trading --create-namespace

# Upgrade
helm upgrade mt5-trading . -n mt5-trading

# Uninstall
helm uninstall mt5-trading -n mt5-trading
```

### Valores Customizados

Crie `my-values.yaml`:

```yaml
# Ambiente de produção
api:
  replicaCount: 3
  apiKey: "your-secure-production-key"

  autoscaling:
    minReplicas: 3
    maxReplicas: 20
    targetCPUUtilizationPercentage: 60

postgres:
  auth:
    password: "your-secure-postgres-password"

  persistence:
    size: 50Gi

grafana:
  auth:
    adminPassword: "your-secure-grafana-password"
```

Deploy com valores customizados:

```bash
helm install mt5-trading . -n mt5-trading -f my-values.yaml
```

### Helm Commands

```bash
# List releases
helm list -n mt5-trading

# Get values
helm get values mt5-trading -n mt5-trading

# Rollback
helm rollback mt5-trading -n mt5-trading

# History
helm history mt5-trading -n mt5-trading
```

---

## 🛠️ Gerenciamento

### Scripts Úteis

#### Deploy

```bash
# Deploy to environment
./scripts/k8s-deploy.sh [dev|staging|production]
```

#### Health Check

```bash
# Check system health
./scripts/k8s-healthcheck.sh [dev|staging|production]
```

#### Scaling

```bash
# Scale deployment
./scripts/k8s-scale.sh [env] [deployment] [replicas]

# Examples:
./scripts/k8s-scale.sh production mt5-api 5
./scripts/k8s-scale.sh dev ml-trainer 2
```

#### Rollback

```bash
# Rollback deployment
./scripts/k8s-rollback.sh [env] [deployment]

# Example:
./scripts/k8s-rollback.sh production mt5-api
```

#### Logs

```bash
# View logs
./scripts/k8s-logs.sh [env] [component]

# Examples:
./scripts/k8s-logs.sh production mt5-api
./scripts/k8s-logs.sh dev postgres
```

### Comandos Kubectl Úteis

```bash
# Get all resources
kubectl get all -n mt5-trading

# Describe pod
kubectl describe pod <pod-name> -n mt5-trading

# Execute command in pod
kubectl exec -it <pod-name> -n mt5-trading -- /bin/bash

# Port forward
kubectl port-forward -n mt5-trading svc/grafana-service 3000:3000

# Get events
kubectl get events -n mt5-trading --sort-by='.lastTimestamp'

# Top pods (resource usage)
kubectl top pods -n mt5-trading
```

---

## 📈 Monitoramento

### Acessar Serviços

#### Port Forwarding

```bash
# API
kubectl port-forward -n mt5-trading svc/mt5-api-service 8000:80

# Grafana
kubectl port-forward -n mt5-trading svc/grafana-service 3000:3000

# Prometheus
kubectl port-forward -n mt5-trading svc/prometheus-service 9090:9090
```

Acesse:

- API: <http://localhost:8000/docs>
- Grafana: <http://localhost:3000> (admin/admin)
- Prometheus: <http://localhost:9090>

#### LoadBalancer (se disponível)

```bash
# Get external IPs
kubectl get svc -n mt5-trading

# API
export API_IP=$(kubectl get svc mt5-api-service -n mt5-trading -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "API: http://$API_IP"

# Grafana
export GRAFANA_IP=$(kubectl get svc grafana-service -n mt5-trading -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Grafana: http://$GRAFANA_IP:3000"
```

### Métricas

```bash
# HPA status
kubectl get hpa -n mt5-trading

# Pod metrics
kubectl top pods -n mt5-trading

# Node metrics
kubectl top nodes
```

---

## 🔍 Troubleshooting

### Pod não inicia

```bash
# Ver status
kubectl get pods -n mt5-trading

# Descrever pod
kubectl describe pod <pod-name> -n mt5-trading

# Ver logs
kubectl logs <pod-name> -n mt5-trading

# Ver logs anterior (se crashed)
kubectl logs <pod-name> -n mt5-trading --previous
```

### ImagePullBackOff

```bash
# Se usando Minikube, carregar imagem
minikube image load mt5-trading-api:latest

# Verificar imagem
kubectl describe pod <pod-name> -n mt5-trading | grep -A 10 "Events:"
```

### Database Connection Issues

```bash
# Verificar se postgres está rodando
kubectl get pods -n mt5-trading -l app=postgres

# Testar conexão do pod da API
kubectl exec -it <api-pod-name> -n mt5-trading -- \
  nc -zv postgres-service 5432

# Ver logs do postgres
kubectl logs -n mt5-trading -l app=postgres
```

### PVC Pending

```bash
# Ver PVCs
kubectl get pvc -n mt5-trading

# Descrever PVC
kubectl describe pvc <pvc-name> -n mt5-trading

# Se usando storage class 'manual', criar PV manualmente
kubectl apply -f k8s/base/persistent-volumes.yaml
```

### Ingress não funciona

```bash
# Verificar ingress controller
kubectl get pods -n ingress-nginx

# Descrever ingress
kubectl describe ingress mt5-trading-ingress -n mt5-trading

# Ver logs do ingress controller
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

### HPA não escala

```bash
# Verificar metrics-server
kubectl get deployment metrics-server -n kube-system

# Se não instalado (Minikube)
minikube addons enable metrics-server

# Ver HPA details
kubectl describe hpa mt5-api-hpa -n mt5-trading
```

---

## 🔐 Segurança

### Secrets Management

**Desenvolvimento:**

```bash
# Criar secrets
kubectl create secret generic mt5-trading-secrets \
  -n mt5-trading \
  --from-literal=POSTGRES_PASSWORD='dev_password' \
  --from-literal=API_KEY='dev_api_key'
```

**Produção (recomendado):**

Use ferramentas externas:

- **HashiCorp Vault**
- **AWS Secrets Manager**
- **Azure Key Vault**
- **Sealed Secrets**

Exemplo com Sealed Secrets:

```bash
# Install
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Criar sealed secret
kubeseal --format yaml < secret.yaml > sealed-secret.yaml

# Apply
kubectl apply -f sealed-secret.yaml
```

---

## 📝 Maintenance

### Backup Database

```bash
# Exec into postgres pod
kubectl exec -it <postgres-pod> -n mt5-trading -- bash

# Criar backup
pg_dump -U trader mt5_trading > /tmp/backup.sql

# Copiar para local
kubectl cp mt5-trading/<postgres-pod>:/tmp/backup.sql ./backup.sql
```

### Update Deployment

```bash
# Update image
kubectl set image deployment/mt5-api \
  api=mt5-trading-api:v2.0.0 \
  -n mt5-trading

# Rollout status
kubectl rollout status deployment/mt5-api -n mt5-trading

# Rollback if needed
kubectl rollout undo deployment/mt5-api -n mt5-trading
```

### Clean Up

```bash
# Delete namespace (⚠️ CUIDADO: deleta tudo!)
kubectl delete namespace mt5-trading-dev

# Delete specific resource
kubectl delete deployment mt5-api -n mt5-trading

# Delete via kustomize
kubectl delete -k k8s/overlays/dev
```

---

## 📚 Referências

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize](https://kustomize.io/)
- [Helm](https://helm.sh/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [Prometheus Operator](https://github.com/prometheus-operator/prometheus-operator)

---

## 🤝 Suporte

Para problemas ou dúvidas:

1. Verificar logs: `kubectl logs <pod> -n mt5-trading`
2. Verificar events: `kubectl get events -n mt5-trading`
3. Executar health check: `./scripts/k8s-healthcheck.sh`
4. Abrir issue no GitHub
