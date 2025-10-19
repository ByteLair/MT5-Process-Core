# ADR-002: Arquitetura de Microserviços com Docker Compose

**Status**: ✅ Aceito  
**Data**: 2025-01-20  
**Autor**: Equipe MT5 Trading  
**Decisores**: Arquitetos de Sistema, DevOps, Tech Lead

## Contexto

O sistema MT5 Trading possui múltiplos componentes com responsabilidades distintas:
- API REST para ingestão de dados e consultas
- ML scheduler para treinamento de modelos
- Banco de dados TimescaleDB
- PgBouncer para connection pooling
- Stack de observabilidade (Prometheus, Grafana, Loki, Promtail, Jaeger)

Precisamos de uma arquitetura que permita:
- **Isolamento**: Cada componente em seu próprio ambiente
- **Escalabilidade**: Escalar serviços individualmente
- **Desenvolvimento**: Facilitar desenvolvimento local
- **Deploy**: Simplicidade no deploy e rollback
- **Manutenção**: Facilidade para atualizar componentes

## Decisão

Adotar **arquitetura de microserviços orquestrada com Docker Compose** para ambiente de desenvolvimento e produção (single-node).

A arquitetura consiste em:
- **Serviços isolados**: Cada componente em container separado
- **Rede Docker**: Comunicação interna via `mt5_network`
- **Volumes nomeados**: Persistência de dados (DB, modelos, configs)
- **Healthchecks**: Monitoramento automático de saúde dos containers
- **Docker Compose**: Orquestração simples sem overhead de Kubernetes

## Alternativas Consideradas

### Alternativa 1: Monolito (Single Container)
- **Prós**: 
  - Simplicidade extrema de deploy
  - Menos overhead de rede
  - Configuração mínima
- **Contras**: 
  - Escalabilidade limitada (tudo ou nada)
  - Acoplamento entre componentes
  - Dificuldade para updates parciais
  - Conflitos de dependências (Python + Node.js + etc)

### Alternativa 2: Kubernetes
- **Prós**: 
  - Escalabilidade horizontal automática
  - Self-healing robusto
  - Load balancing nativo
  - Multi-node clustering
- **Contras**: 
  - Complexidade operacional muito alta
  - Overhead de recursos (control plane)
  - Curva de aprendizado íngreme
  - Overkill para single-node deployment
  - Custos de infraestrutura maiores

### Alternativa 3: Docker Swarm
- **Prós**: 
  - Orquestração multi-node
  - Sintaxe similar ao Compose
  - Mais simples que Kubernetes
- **Contras**: 
  - Ecosystem menor
  - Menos features que Kubernetes
  - Community menor (less momentum)
  - Overkill para nossa escala atual

## Consequências

### Positivas

- ✅ **Isolamento**: Cada serviço em seu próprio container com dependências isoladas
- ✅ **Escalabilidade Vertical**: Fácil ajustar recursos (CPU, RAM) por serviço
- ✅ **Desenvolvimento Local**: `docker compose up` para ambiente completo
- ✅ **Rollback Rápido**: `docker compose down && docker compose up` com versões antigas
- ✅ **Debugging**: Logs isolados por container (`docker logs <service>`)
- ✅ **CI/CD**: Build e deploy de serviços individuais
- ✅ **Observabilidade**: Integração nativa com Prometheus (container metrics)
- ✅ **Simplicidade**: Menos complexidade que Kubernetes para escala atual

### Negativas

- ❌ **Single-Node**: Não suporta multi-node clustering nativamente
- ❌ **No Auto-Scaling**: Scaling manual via `docker compose up --scale`
- ❌ **Service Discovery**: Limitado (via DNS interno, sem service mesh)
- ❌ **Secrets Management**: Arquivos .env expostos (mitigado: permissões restritas)

### Riscos

- ⚠️ **Crescimento de Tráfego**: Se escala exceder capacidade single-node
  - **Mitigação**: Monitorar métricas, planejar migração para K8s se necessário
- ⚠️ **Downtime em Updates**: Restart de containers causa breve indisponibilidade
  - **Mitigação**: Maintenance windows agendadas, blue-green deployment futuro
- ⚠️ **Container Crashes**: Sem self-healing automático
  - **Mitigação**: Systemd units com restart automático, alertas Grafana

## Detalhes de Implementação

### Estrutura Docker Compose

```yaml
version: "3.8"

services:
  db:
    image: timescale/timescaledb:latest-pg15
    container_name: mt5_db
    environment:
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: mt5_trading
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d
    networks:
      - mt5_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trader"]
      interval: 10s
      timeout: 5s
      retries: 5

  pgbouncer:
    image: edoburu/pgbouncer
    container_name: mt5_pgbouncer
    environment:
      DATABASE_URL: "postgres://trader:${DB_PASSWORD}@db:5432/mt5_trading"
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 1000
    depends_on:
      - db
    networks:
      - mt5_network

  api:
    build: ./api
    container_name: mt5_api
    ports:
      - "8001:8000"
    environment:
      DATABASE_URL: "postgresql://trader:${DB_PASSWORD}@pgbouncer:6432/mt5_trading"
      MODELS_DIR: "/models"
    volumes:
      - ./api:/app
      - ml_models:/models
      - api_logs:/app/logs
    depends_on:
      - pgbouncer
    networks:
      - mt5_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ml:
    build: ./ml
    container_name: mt5_ml
    environment:
      DATABASE_URL: "postgresql://trader:${DB_PASSWORD}@pgbouncer:6432/mt5_trading"
      MODELS_DIR: "/models"
    volumes:
      - ./ml:/app
      - ml_models:/models
      - ml_logs:/app/logs
    depends_on:
      - pgbouncer
    networks:
      - mt5_network

  prometheus:
    image: prom/prometheus:latest
    container_name: mt5_prometheus
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - mt5_network

  grafana:
    image: grafana/grafana:latest
    container_name: mt5_grafana
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    depends_on:
      - prometheus
    networks:
      - mt5_network

  loki:
    image: grafana/loki:latest
    container_name: mt5_loki
    volumes:
      - ./loki:/etc/loki
      - loki_data:/loki
    ports:
      - "3100:3100"
    networks:
      - mt5_network

  promtail:
    image: grafana/promtail:latest
    container_name: mt5_promtail
    volumes:
      - ./promtail:/etc/promtail
      - api_logs:/var/log/api:ro
      - ml_logs:/var/log/ml:ro
    depends_on:
      - loki
    networks:
      - mt5_network

  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: mt5_jaeger
    ports:
      - "16686:16686"
      - "14268:14268"
    networks:
      - mt5_network

networks:
  mt5_network:
    driver: bridge

volumes:
  db_data:
  ml_models:
  prometheus_data:
  grafana_data:
  loki_data:
  api_logs:
  ml_logs:
```

### Padrões de Comunicação

```
Cliente → API (8001) → PgBouncer (6432) → TimescaleDB (5432)
                   ↓
             ML Scheduler → Models Volume
                   ↓
            Prometheus (9090) ← Scrape metrics
                   ↓
            Grafana (3000) → Visualização
                   ↓
            Loki (3100) ← Promtail ← Logs
```

### Comandos de Gestão

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Logs
docker compose logs -f api

# Restart single service
docker compose restart api

# Scale (horizontal)
docker compose up --scale api=3 -d

# Rebuild
docker compose build --no-cache api
docker compose up -d api
```

### Health Monitoring

```bash
# Check all containers
docker compose ps

# Automated health check script
./scripts/health-check.sh
```

## Referências

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [12 Factor App](https://12factor.net/)
- [Microservices Patterns](https://microservices.io/patterns/microservices.html)
- [Docker Compose vs Kubernetes](https://www.docker.com/blog/kubernetes-vs-docker-compose/)
- Benchmark interno: `docs/benchmarks/docker_performance.md`
