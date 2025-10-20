# ☸️ Kubernetes Quick Reference

Comandos rápidos para gerenciar a plataforma MT5 Trading em Kubernetes.

---

## 🚀 Deployment

```bash
# Deploy completo (dev)
./scripts/k8s-deploy.sh dev

# Deploy completo (production)
./scripts/k8s-deploy.sh production

# Deploy com Kustomize
kubectl apply -k k8s/overlays/dev

# Deploy com Helm
helm install mt5-trading ./helm/mt5-trading -n mt5-trading
```

---

## 📊 Status & Monitoring

```bash
# Health check completo
./scripts/k8s-healthcheck.sh production

# Ver todos os recursos
kubectl get all -n mt5-trading

# Ver pods
kubectl get pods -n mt5-trading -o wide

# Ver deployments
kubectl get deployments -n mt5-trading

# Ver services
kubectl get svc -n mt5-trading

# Ver HPA
kubectl get hpa -n mt5-trading

# Ver PVCs
kubectl get pvc -n mt5-trading

# Top pods (CPU/Memory)
kubectl top pods -n mt5-trading

# Events
kubectl get events -n mt5-trading --sort-by='.lastTimestamp'
```

---

## 📝 Logs

```bash
# Logs de um componente (tail + follow)
./scripts/k8s-logs.sh production mt5-api

# Logs de um pod específico
kubectl logs -f <pod-name> -n mt5-trading

# Logs de todos os pods de um deployment
kubectl logs -f -l app=mt5-api -n mt5-trading --prefix

# Logs de crash anterior
kubectl logs <pod-name> -n mt5-trading --previous

# Últimas 100 linhas
kubectl logs <pod-name> -n mt5-trading --tail=100
```

---

## 🔧 Management

```bash
# Scale manual
./scripts/k8s-scale.sh production mt5-api 5

# Scale com kubectl
kubectl scale deployment/mt5-api --replicas=5 -n mt5-trading

# Restart deployment
kubectl rollout restart deployment/mt5-api -n mt5-trading

# Status do rollout
kubectl rollout status deployment/mt5-api -n mt5-trading

# Histórico
kubectl rollout history deployment/mt5-api -n mt5-trading

# Rollback
./scripts/k8s-rollback.sh production mt5-api

# Rollback com kubectl
kubectl rollout undo deployment/mt5-api -n mt5-trading
```

---

## 🐛 Debugging

```bash
# Descrever pod
kubectl describe pod <pod-name> -n mt5-trading

# Exec no container
kubectl exec -it <pod-name> -n mt5-trading -- /bin/bash

# Exec em deployment específico
kubectl exec -it deployment/mt5-api -n mt5-trading -- /bin/bash

# Ver variáveis de ambiente
kubectl exec <pod-name> -n mt5-trading -- env

# Testar conectividade
kubectl exec <pod-name> -n mt5-trading -- nc -zv postgres-service 5432

# Port forward para debug
kubectl port-forward <pod-name> -n mt5-trading 8000:8000
```

---

## 🌐 Acesso aos Serviços

```bash
# API
kubectl port-forward -n mt5-trading svc/mt5-api-service 8000:80
# http://localhost:8000/docs

# Grafana
kubectl port-forward -n mt5-trading svc/grafana-service 3000:3000
# http://localhost:3000 (admin/admin)

# Prometheus
kubectl port-forward -n mt5-trading svc/prometheus-service 9090:9090
# http://localhost:9090

# PostgreSQL (local)
kubectl port-forward -n mt5-trading svc/postgres-service 5432:5432
# psql -h localhost -U trader -d mt5_trading
```

---

## 🔐 Secrets

```bash
# Ver secrets
kubectl get secrets -n mt5-trading

# Descrever secret
kubectl describe secret mt5-trading-secrets -n mt5-trading

# Ver valor de secret (base64 decoded)
kubectl get secret mt5-trading-secrets -n mt5-trading -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d

# Criar secret
kubectl create secret generic mt5-trading-secrets \
  -n mt5-trading \
  --from-literal=POSTGRES_PASSWORD='new_password' \
  --from-literal=API_KEY='new_api_key' \
  --dry-run=client -o yaml | kubectl apply -f -

# Deletar secret
kubectl delete secret mt5-trading-secrets -n mt5-trading
```

---

## 📦 ConfigMaps

```bash
# Ver configmaps
kubectl get configmap -n mt5-trading

# Descrever configmap
kubectl describe configmap mt5-trading-config -n mt5-trading

# Editar configmap
kubectl edit configmap mt5-trading-config -n mt5-trading

# Ver conteúdo
kubectl get configmap mt5-trading-config -n mt5-trading -o yaml
```

---

## 💾 Storage

```bash
# Ver PVs
kubectl get pv

# Ver PVCs
kubectl get pvc -n mt5-trading

# Descrever PVC
kubectl describe pvc postgres-pvc -n mt5-trading

# Ver uso de disco (dentro do pod)
kubectl exec <pod-name> -n mt5-trading -- df -h
```

---

## 🔄 Updates

```bash
# Atualizar imagem
kubectl set image deployment/mt5-api api=mt5-trading-api:v2.0.1 -n mt5-trading

# Apply new config
kubectl apply -k k8s/overlays/production

# Helm upgrade
helm upgrade mt5-trading ./helm/mt5-trading -n mt5-trading

# Verify update
kubectl rollout status deployment/mt5-api -n mt5-trading
```

---

## 🧹 Cleanup

```bash
# Deletar deployment
kubectl delete deployment mt5-api -n mt5-trading

# Deletar service
kubectl delete service mt5-api-service -n mt5-trading

# Deletar tudo do namespace (⚠️ CUIDADO!)
kubectl delete all --all -n mt5-trading

# Deletar namespace completo (⚠️ CUIDADO!)
kubectl delete namespace mt5-trading

# Deletar via kustomize
kubectl delete -k k8s/overlays/dev

# Uninstall Helm
helm uninstall mt5-trading -n mt5-trading
```

---

## 📈 Metrics & Monitoring

```bash
# Métricas do pod
kubectl top pod <pod-name> -n mt5-trading

# Métricas de todos os pods
kubectl top pods -n mt5-trading

# Métricas dos nodes
kubectl top nodes

# HPA status
kubectl get hpa mt5-api-hpa -n mt5-trading -w

# Describe HPA
kubectl describe hpa mt5-api-hpa -n mt5-trading
```

---

## 🔍 Troubleshooting Quick Commands

```bash
# Pod não inicia
kubectl describe pod <pod-name> -n mt5-trading | grep -A 10 "Events:"
kubectl logs <pod-name> -n mt5-trading

# ImagePullBackOff
kubectl describe pod <pod-name> -n mt5-trading | grep "Image:"
minikube image load mt5-trading-api:latest  # Se Minikube

# CrashLoopBackOff
kubectl logs <pod-name> -n mt5-trading --previous
kubectl describe pod <pod-name> -n mt5-trading

# PVC Pending
kubectl describe pvc <pvc-name> -n mt5-trading
kubectl get pv

# Service não acessível
kubectl get endpoints -n mt5-trading
kubectl describe svc <service-name> -n mt5-trading

# Ingress não funciona
kubectl describe ingress mt5-trading-ingress -n mt5-trading
kubectl get pods -n ingress-nginx
```

---

## 🎯 Common Tasks

### Verificar se tudo está OK

```bash
./scripts/k8s-healthcheck.sh production
```

### Ver logs da API em tempo real

```bash
./scripts/k8s-logs.sh production mt5-api
```

### Escalar API para 5 réplicas

```bash
./scripts/k8s-scale.sh production mt5-api 5
```

### Fazer rollback da API

```bash
./scripts/k8s-rollback.sh production mt5-api
```

### Backup do database

```bash
kubectl exec -it <postgres-pod> -n mt5-trading -- \
  pg_dump -U trader mt5_trading > backup.sql
```

### Restore do database

```bash
kubectl cp backup.sql mt5-trading/<postgres-pod>:/tmp/
kubectl exec -it <postgres-pod> -n mt5-trading -- \
  psql -U trader mt5_trading < /tmp/backup.sql
```

### Reiniciar todos os pods

```bash
kubectl rollout restart deployment/postgres -n mt5-trading
kubectl rollout restart deployment/mt5-api -n mt5-trading
kubectl rollout restart deployment/ml-trainer -n mt5-trading
kubectl rollout restart deployment/prometheus -n mt5-trading
kubectl rollout restart deployment/grafana -n mt5-trading
```

### Verificar recursos (CPU/Memory)

```bash
kubectl top pods -n mt5-trading
kubectl describe node | grep -A 5 "Allocated resources"
```

---

## 📚 Docs

- **Guia Completo**: [docs/K8S_DEPLOYMENT.md](K8S_DEPLOYMENT.md)
- **Sumário**: [docs/K8S_IMPLEMENTATION_SUMMARY.md](K8S_IMPLEMENTATION_SUMMARY.md)
- **README**: [README.md](../README.md)

---

## 🆘 Help

```bash
# kubectl help
kubectl --help
kubectl get --help
kubectl describe --help

# Kustomize help
kustomize build --help

# Helm help
helm --help
helm install --help

# Scripts help
./scripts/k8s-deploy.sh  # Mostra usage
./scripts/k8s-healthcheck.sh
```

---

**Última atualização**: 18/10/2025
**Versão**: 2.0.0
