# 📝 Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-10-18

### 📚 Documentation Overhaul - Complete Technical Documentation

This release focuses on **comprehensive documentation** for the entire system, making it accessible to both new developers and operators.

### Added

#### Complete Documentation Suite

- ✨ **Technical Documentation** (`docs/DOCUMENTATION.md`) - 500+ lines
  - Complete system architecture
  - Installation and configuration guide
  - API reference with all endpoints
  - ML pipeline detailed explanation
  - Monitoring and observability setup
  - Backup and disaster recovery procedures
  - Automation and maintenance guide
  - Security best practices
  - Comprehensive troubleshooting guide

- ✨ **Visual Diagrams** (`docs/DIAGRAMS.md`)
  - 10 Mermaid diagrams covering architecture, data flows, monitoring, automation, backup, health checks, CI/CD, and database schema

- ✨ **Onboarding Guide** (`docs/ONBOARDING.md`)
  - 5-day structured tutorial for new developers
  - Day 1-5: Setup, exploration, first contribution, ML understanding, operations

- ✨ **Practical Examples** (`docs/EXAMPLES.md`)
  - 50+ code snippets for common tasks (adding symbols, models, endpoints, dashboards, metrics, alerts)

- ✨ **Architecture Decision Records** (`docs/adr/`)
  - ADR-001: TimescaleDB, ADR-002: Docker Compose, ADR-005: Random Forest

- ✨ **Performance Guidelines** (`docs/PERFORMANCE.md`)
  - Benchmarks, limits, optimizations, monitoring, troubleshooting

- ✨ **Operational Runbook** (`docs/RUNBOOK.md`)
  - Daily operations, deploy/rollback, backup/restore, incident response, disaster recovery

- ✨ **Glossary** (`docs/GLOSSARY.md`)
  - 80+ terms: trading, indicators, ML, infrastructure, database, observability

- ✨ **FAQ** (`docs/FAQ.md`)
  - 50+ Q&A covering installation, development, troubleshooting, performance

### Documentation Statistics

- **New Files**: 9
- **Lines**: 4,000+
- **Diagrams**: 10
- **Examples**: 50+
- **Terms**: 80+
- **FAQ**: 50+

---

## [2.0.0] - 2025-10-18

### 🚀 Major Release - Kubernetes & Infrastructure Upgrade

This is a major release focused on **production-ready Kubernetes deployment** and **comprehensive infrastructure improvements**.

### Added

#### Kubernetes Infrastructure

- ✨ Complete Kubernetes manifests for all services
- ✨ Kustomize overlays for dev/staging/production environments
- ✨ Helm Chart v2.0.0 with 200+ configuration options
- ✨ HorizontalPodAutoscaler for API (2-10 replicas)
- ✨ PersistentVolumes for data persistence (37Gi total)
- ✨ NGINX Ingress with TLS support
- ✨ RBAC and ServiceAccounts for security
- ✨ CronJob for automated ML training

#### Scripts & Automation

- ✨ `k8s-deploy.sh` - Automated deployment to K8s
- ✨ `k8s-healthcheck.sh` - Comprehensive health verification
- ✨ `k8s-scale.sh` - Manual scaling helper
- ✨ `k8s-rollback.sh` - One-command rollback
- ✨ `k8s-logs.sh` - Centralized log viewing

#### Terraform Infrastructure

- ✨ Complete Terraform configuration for Docker
- ✨ Infrastructure as Code for all services
- ✨ Variables and outputs for easy configuration
- ✨ terraform/ directory with main.tf, variables.tf, outputs.tf

#### Grafana Dashboard

- ✨ 10-panel main dashboard with auto-provisioning
- ✨ Datasources: Prometheus + PostgreSQL
- ✨ 6 alert rules (API down, latency, errors, etc.)
- ✨ grafana/ directory with provisioning configs

#### Prometheus Metrics

- ✨ `ingest_candles_inserted_total` - Counter for total candles
- ✨ `ingest_requests_total{method,status}` - Request counter
- ✨ `ingest_duplicates_total{symbol,timeframe}` - Duplicate tracking
- ✨ `ingest_latency_seconds` - Histogram with 9 buckets
- ✨ `ingest_batch_size` - Histogram for batch analysis

#### Documentation

- ✨ `K8S_DEPLOYMENT.md` - Complete Kubernetes guide (400+ lines)
- ✨ `K8S_IMPLEMENTATION_SUMMARY.md` - Implementation overview
- ✨ `TERRAFORM_DASHBOARD_SUMMARY.md` - Infrastructure summary
- ✨ `EA_INTEGRATION_GUIDE.md` - Windows EA integration
- ✨ `SQL_QUERIES.md` - 21 useful SQL queries
- ✨ Updated README.md with all new features

#### Utility Scripts

- ✨ `quickstart.sh` - Quick start with health checks
- ✨ `healthcheck.sh` - System health verification
- ✨ `backup.sh` - Automated backup (DB + Models + Configs)

### Changed

#### API Enhancements

- 🔄 Enhanced `/ingest` endpoint with Prometheus metrics
- 🔄 Improved error tracking and logging
- 🔄 Better duplicate detection
- 🔄 Latency measurement per request

#### Docker Compose

- 🔄 Updated with Grafana provisioning volume
- 🔄 Removed duplicate CSV volume mount
- 🔄 Added prometheus, grafana, pgadmin services
- 🔄 Enhanced with monitoring stack

#### Database

- 🔄 Optimized queries for better performance
- 🔄 Added continuous aggregates
- 🔄 Improved indexing strategy

### Fixed

- 🐛 Fixed Grafana provisioning not loading on first start
- 🐛 Fixed Prometheus metrics endpoint returning 307 redirect
- 🐛 Fixed healthcheck script string matching
- 🐛 Fixed Docker Compose volume conflicts

### Infrastructure Statistics

- **New Files**: 25+
- **Lines of Code**: 3,500+
- **Documentation**: 1,000+ lines
- **Kubernetes Manifests**: 11
- **Scripts**: 10
- **Total Storage (K8s)**: 37Gi

### Deployment Methods

1. **Docker Compose** - Local development
2. **Terraform** - Infrastructure as Code
3. **Kubernetes (Kustomize)** - GitOps compatible
4. **Kubernetes (Helm)** - Package management

---

## [1.0.0] - 2024-10-18

### Initial Release

#### Added

- ✨ FastAPI backend with authentication
- ✨ TimescaleDB for time-series data
- ✨ PostgreSQL with hypertables
- ✨ ML models (RandomForest, Informer)
- ✨ Docker Compose setup
- ✨ Basic monitoring
- ✨ API endpoints: /ingest, /metrics, /signals, /predict

#### Machine Learning

- ✨ RandomForest regressor for price prediction
- ✨ Informer (Transformer) for classification
- ✨ 18+ technical indicators as features
- ✨ Automated training pipeline

#### Database

- ✨ TimescaleDB hypertables
- ✨ Continuous aggregates
- ✨ Optimized indexes
- ✨ Market data table with partitioning

#### API Features

- ✨ API Key authentication
- ✨ Rate limiting
- ✨ Input validation
- ✨ Swagger documentation
- ✨ Health check endpoint

---

## Version Comparison

### v2.0.0 vs v1.0.0

| Feature | v1.0.0 | v2.0.0 |
|---------|--------|--------|
| **Deployment** | Docker Compose only | Docker Compose + Terraform + K8s |
| **Environments** | Single | 3 (dev/staging/prod) |
| **Scaling** | Manual | Auto (HPA) |
| **Monitoring** | Basic | Prometheus + Grafana (10 panels) |
| **Metrics** | None | 5 custom metrics |
| **Alerts** | None | 6 alert rules |
| **Documentation** | Basic | 1,000+ lines |
| **Scripts** | Few | 10+ automation scripts |
| **Infrastructure as Code** | No | Yes (Terraform + K8s) |
| **High Availability** | No | Yes (replicas + autoscaling) |
| **Storage** | Local volumes | PersistentVolumes (37Gi) |
| **Ingress** | No | NGINX + TLS |
| **RBAC** | No | Yes (ServiceAccounts + Roles) |
| **Backup** | Manual | Automated script |
| **Health Checks** | Basic | Comprehensive |

**Lines of Code Added**: ~3,500
**Files Added**: ~25
**Production Readiness**: ⬆️ Significantly Improved

---

## Upcoming Features

### v2.1.0 (Planned)

- [ ] StatefulSet for PostgreSQL HA
- [ ] NetworkPolicies for pod isolation
- [ ] Advanced logging with Loki
- [ ] Distributed tracing with Jaeger
- [ ] Service Mesh integration (Istio/Linkerd)

### v2.2.0 (Planned)

- [ ] Multi-region deployment
- [ ] Advanced ML models (LSTM, GRU)
- [ ] Real-time streaming with Kafka
- [ ] Advanced backtesting engine
- [ ] Web UI dashboard

### v3.0.0 (Future)

- [ ] Microservices architecture
- [ ] Event-driven design
- [ ] Multi-cloud support
- [ ] Advanced security features
- [ ] Chaos engineering tests

---

## Migration Guide

### From v1.0.0 to v2.0.0

#### Docker Compose Users

No breaking changes! Continue using:

```bash
docker compose up -d
```

New features available:

- Grafana dashboard: <http://localhost:3000>
- Prometheus: <http://localhost:9090>
- Enhanced metrics: <http://localhost:18001/prometheus>

#### Upgrading to Kubernetes

1. **Build new images**:

```bash
docker build -t mt5-trading-api:latest -f api/Dockerfile ./api
docker build -t mt5-trading-ml:latest -f ml/Dockerfile ./ml
```

2. **Deploy to K8s**:

```bash
./scripts/k8s-deploy.sh production
```

3. **Migrate data**:

```bash
# Backup from Docker Compose
./backup.sh

# Restore to K8s
kubectl cp backup.tar.gz mt5-trading/postgres-pod:/tmp/
kubectl exec -it postgres-pod -n mt5-trading -- bash
# Inside pod: restore database
```

#### Breaking Changes

**None!** v2.0.0 is fully backward compatible.

---

## Support

For issues, questions, or contributions:

- 📧 GitHub Issues
- 📚 Documentation: `/docs` directory
- 🔍 Troubleshooting guides in README.md

---

**Maintained by**: Felipe
**Repository**: <https://github.com/Lysk-dot/mt5-trading-db>
**License**: MIT
