# 🚀 Sugestões de Melhorias na Infraestrutura

> **Análise:** Outubro 2025  
> **Status Atual:** Infraestrutura sólida com Docker, K8s, Terraform, Grafana  
> **Próximos Passos:** Otimizações e hardening

---

## 📊 Análise Atual

### ✅ Pontos Fortes
- ✓ Monitoramento robusto (Prometheus + Grafana)
- ✓ Kubernetes pronto para produção
- ✓ TimescaleDB para séries temporais
- ✓ CI/CD básico com scripts
- ✓ Documentação organizada

### ⚠️ Oportunidades de Melhoria
- Backups automatizados limitados
- Secrets em plain text (.env)
- Ausência de CI/CD pipeline completo
- Cache não implementado
- Rate limiting básico
- Disaster recovery não documentado

---

## 🎯 Melhorias Recomendadas

### 🔴 **PRIORIDADE ALTA** (Implementar Imediatamente)

#### 1. **Sistema de Backups Robusto**

**Problema:** Backups existem mas não são testados regularmente

**Solução:**
```yaml
# docker-compose.yml - Adicionar serviço de backup
services:
  backup:
    image: prodrigestivill/postgres-backup-local:16
    container_name: mt5_backup
    restart: unless-stopped
    env_file: .env
    environment:
      POSTGRES_HOST: db
      POSTGRES_DB: mt5_trading
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: trader123
      SCHEDULE: "@daily"  # Backup diário às 00:00
      BACKUP_KEEP_DAYS: 7
      BACKUP_KEEP_WEEKS: 4
      BACKUP_KEEP_MONTHS: 6
      HEALTHCHECK_PORT: 8080
    volumes:
      - ./backups:/backups
      - /etc/localtime:/etc/localtime:ro
    depends_on:
      db:
        condition: service_healthy
    networks:
      - default
```

**Script de Teste de Restore:**
```bash
#!/bin/bash
# scripts/test_backup_restore.sh

set -e

BACKUP_DIR="./backups"
TEST_DB="mt5_trading_test"

echo "🧪 Testando restore do último backup..."

# Pega último backup
LATEST_BACKUP=$(ls -t $BACKUP_DIR/*.sql.gz | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "❌ Nenhum backup encontrado!"
    exit 1
fi

echo "📦 Backup: $LATEST_BACKUP"

# Cria DB de teste
docker compose exec -T db psql -U trader -c "DROP DATABASE IF EXISTS $TEST_DB;"
docker compose exec -T db psql -U trader -c "CREATE DATABASE $TEST_DB;"

# Restaura backup
gunzip -c "$LATEST_BACKUP" | docker compose exec -T db psql -U trader -d $TEST_DB

# Valida dados
COUNT=$(docker compose exec -T db psql -U trader -d $TEST_DB -t -c "SELECT COUNT(*) FROM market_data;")

echo "✅ Restore OK! $COUNT registros encontrados"
echo "🧹 Limpando DB de teste..."
docker compose exec -T db psql -U trader -c "DROP DATABASE $TEST_DB;"
```

**Cronjob para teste semanal:**
```bash
# Adicionar ao crontab
0 3 * * 0 cd /home/felipe/mt5-trading-db && ./scripts/test_backup_restore.sh >> ./logs/backup_test.log 2>&1
```

---

#### 2. **Secrets Management com Vault ou SOPS**

**Problema:** Senhas em `.env` plain text

**Solução A - Docker Secrets (Mais simples):**
```bash
# Criar secrets
echo "trader123" | docker secret create db_password -
echo "mt5_trading_secure_key_2025_prod" | docker secret create api_key -

# docker-compose.yml
services:
  db:
    secrets:
      - db_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
  
  api:
    secrets:
      - api_key
      - db_password

secrets:
  db_password:
    external: true
  api_key:
    external: true
```

**Solução B - HashiCorp Vault (Mais robusto):**
```yaml
# docker-compose.yml
services:
  vault:
    image: hashicorp/vault:1.15
    container_name: mt5_vault
    restart: unless-stopped
    cap_add:
      - IPC_LOCK
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: ${VAULT_ROOT_TOKEN}
      VAULT_DEV_LISTEN_ADDRESS: 0.0.0.0:8200
    ports:
      - "8200:8200"
    volumes:
      - vault_data:/vault/data
    command: server -dev

volumes:
  vault_data:
```

**Script de inicialização:**
```bash
#!/bin/bash
# scripts/setup_vault.sh

export VAULT_ADDR='http://localhost:8200'
export VAULT_TOKEN='root-token'

# Habilita secrets engine
vault secrets enable -path=mt5 kv-v2

# Adiciona secrets
vault kv put mt5/database password=trader123
vault kv put mt5/api key=mt5_trading_secure_key_2025_prod

# Cria policy para API
vault policy write mt5-api - <<EOF
path "mt5/data/*" {
  capabilities = ["read", "list"]
}
EOF

# Cria token para API
vault token create -policy=mt5-api -ttl=720h
```

---

#### 3. **Redis Cache para Queries Pesadas**

**Problema:** Queries repetitivas sem cache

**Solução:**
```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7.2-alpine
    container_name: mt5_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "1"
          memory: "512m"

volumes:
  redis_data:
```

**Implementação no código:**
```python
# api/cache.py
import redis
import json
from functools import wraps
from typing import Any, Callable
import hashlib

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

def cache_result(ttl: int = 300):
    """Cache decorator for expensive queries"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Generate cache key from function name and arguments
            key_parts = [func.__name__] + [str(arg) for arg in args]
            key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )
            
            return result
        return wrapper
    return decorator

# Uso em endpoints
@router.get("/symbols")
@cache_result(ttl=3600)  # Cache por 1 hora
async def get_symbols():
    # Query pesada aqui
    pass
```

---

### 🟡 **PRIORIDADE MÉDIA** (Implementar em 2-4 semanas)

#### 4. **CI/CD Pipeline Completo**

**Solução - GitHub Actions:**
```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r api/requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        run: |
          pytest api/tests/ --cov=api --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: |
          docker build -t mt5-api:${{ github.sha }} ./api
      
      - name: Scan image for vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: mt5-api:${{ github.sha }}
          severity: 'CRITICAL,HIGH'

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # SSH para servidor e atualizar
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} << 'EOF'
            cd /home/felipe/mt5-trading-db
            git pull
            docker compose pull
            docker compose up -d --no-deps api
          EOF
```

**Testes unitários básicos:**
```python
# api/tests/test_endpoints.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_symbols_endpoint():
    response = client.get("/symbols")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_ingest_requires_auth():
    response = client.post("/ingest", json={})
    assert response.status_code == 401
```

---

#### 5. **Rate Limiting e DDoS Protection**

**Solução com Nginx:**
```nginx
# nginx/nginx.conf
http {
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=ingest_limit:10m rate=100r/s;
    
    upstream api_backend {
        server api:8001;
    }
    
    server {
        listen 80;
        server_name mt5-trading.local;
        
        location /api {
            limit_req zone=api_limit burst=20 nodelay;
            limit_req_status 429;
            
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
        
        location /ingest {
            limit_req zone=ingest_limit burst=200 nodelay;
            
            # Apenas IPs permitidos
            allow 192.168.15.0/24;  # Rede local
            deny all;
            
            proxy_pass http://api_backend;
        }
    }
}
```

**Docker Compose:**
```yaml
services:
  nginx:
    image: nginx:1.25-alpine
    container_name: mt5_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
```

---

#### 6. **Connection Pooling Otimizado**

**Problema:** Conexões não otimizadas com o banco

**Solução:**
```python
# api/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,              # Conexões permanentes
    max_overflow=40,           # Conexões extras sob demanda
    pool_timeout=30,           # Timeout para obter conexão
    pool_recycle=3600,         # Reciclar conexões a cada 1h
    pool_pre_ping=True,        # Verificar se conexão está viva
    echo=False,                # Logs SQL
    connect_args={
        "server_settings": {
            "application_name": "mt5_api",
            "jit": "off"       # Desabilitar JIT se causar lentidão
        },
        "command_timeout": 60,
        "timeout": 10
    }
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

**PostgreSQL tuning:**
```sql
-- docker/postgres.conf.d/postgresql.conf
# Conexões
max_connections = 200
superuser_reserved_connections = 3

# Connection pooling com PgBouncer (recomendado)
# Adicionar serviço PgBouncer no docker-compose
```

**PgBouncer:**
```yaml
services:
  pgbouncer:
    image: edoburu/pgbouncer:1.21.0
    container_name: mt5_pgbouncer
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://trader:trader123@db:5432/mt5_trading
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 500
      DEFAULT_POOL_SIZE: 25
    ports:
      - "6432:5432"
    depends_on:
      - db
```

---

### 🟢 **PRIORIDADE BAIXA** (Melhorias Futuras)

#### 7. **Message Queue para Processamento Assíncrono**

```yaml
services:
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    container_name: mt5_rabbitmq
    restart: unless-stopped
    environment:
      RABBITMQ_DEFAULT_USER: trader
      RABBITMQ_DEFAULT_PASS: trader123
    ports:
      - "5672:5672"   # AMQP
      - "15672:15672" # Management UI
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  celery_worker:
    build: ./api
    container_name: mt5_celery_worker
    restart: unless-stopped
    command: celery -A app.worker worker --loglevel=info
    depends_on:
      - rabbitmq
      - redis
    env_file: .env

volumes:
  rabbitmq_data:
```

---

#### 8. **Disaster Recovery Plan**

**Documentação:**
```markdown
# DISASTER_RECOVERY.md

## 🚨 Plano de Recuperação de Desastres

### Cenário 1: Perda Total do Servidor
**RTO (Recovery Time Objective):** 4 horas
**RPO (Recovery Point Objective):** 24 horas

1. Provisionar novo servidor (1h)
2. Instalar Docker/Docker Compose (30min)
3. Clonar repositório (5min)
4. Restaurar último backup (2h)
5. Validar dados (30min)

### Cenário 2: Corrupção do Banco de Dados
**RTO:** 2 horas
**RPO:** 1 hora

1. Parar serviços
2. Restaurar backup mais recente
3. Aplicar WAL logs se disponíveis
4. Validar integridade
5. Reiniciar serviços

### Backups Offsite
- **Diário:** S3/Backblaze B2
- **Semanal:** HD externo
- **Mensal:** Cloud archive (Glacier)
```

---

#### 9. **Observabilidade Avançada**

**Loki para Logs:**
```yaml
services:
  loki:
    image: grafana/loki:2.9.0
    container_name: mt5_loki
    restart: unless-stopped
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/loki
      - ./loki/config.yaml:/etc/loki/config.yaml
    command: -config.file=/etc/loki/config.yaml

  promtail:
    image: grafana/promtail:2.9.0
    container_name: mt5_promtail
    restart: unless-stopped
    volumes:
      - /var/log:/var/log:ro
      - ./logs:/app/logs:ro
      - ./promtail/config.yaml:/etc/promtail/config.yaml
    command: -config.file=/etc/promtail/config.yaml
```

**Jaeger para Tracing:**
```yaml
services:
  jaeger:
    image: jaegertracing/all-in-one:1.51
    container_name: mt5_jaeger
    restart: unless-stopped
    ports:
      - "6831:6831/udp"
      - "16686:16686"
    environment:
      COLLECTOR_OTLP_ENABLED: true
```

---

#### 10. **Auto-scaling no Kubernetes**

```yaml
# k8s/base/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
```

---

## 📋 Roadmap de Implementação

### Semana 1-2
- [ ] Sistema de backup robusto + testes
- [ ] Secrets management (Docker Secrets ou Vault)
- [ ] Redis cache básico

### Semana 3-4
- [ ] CI/CD pipeline
- [ ] Rate limiting com Nginx
- [ ] Connection pooling otimizado

### Mês 2
- [ ] Message queue (RabbitMQ/Celery)
- [ ] Disaster recovery plan
- [ ] Testes de carga

### Mês 3+
- [ ] Observabilidade avançada (Loki + Jaeger)
- [ ] Multi-region deployment
- [ ] Auto-scaling avançado

---

## 💰 Estimativa de Custos

### Infraestrutura Adicional

| Serviço | Recurso | Custo/Mês |
|---------|---------|-----------|
| Vault | 512MB RAM | Grátis (self-hosted) |
| Redis | 512MB RAM | Grátis (self-hosted) |
| RabbitMQ | 1GB RAM | Grátis (self-hosted) |
| Backups S3 | 100GB | ~$2.30 USD |
| Loki | 2GB RAM | Grátis (self-hosted) |
| **Total** | | **~$2.30 USD/mês** |

### Tempo de Implementação

| Melhoria | Complexidade | Tempo |
|----------|--------------|-------|
| Backups | Baixa | 4h |
| Secrets | Média | 8h |
| Cache | Baixa | 6h |
| CI/CD | Alta | 16h |
| Rate Limit | Baixa | 4h |
| Connection Pool | Média | 6h |
| Message Queue | Alta | 12h |
| DR Plan | Média | 8h |

---

## 🎯 Próximos Passos Imediatos

1. **Hoje:** Implementar sistema de backup automatizado
2. **Esta semana:** Configurar Redis cache
3. **Próxima semana:** Migrar secrets para Vault
4. **Mês atual:** Completar CI/CD pipeline

---

## 📚 Referências

- [TimescaleDB Best Practices](https://docs.timescale.com/use-timescale/latest/best-practices/)
- [Docker Security](https://docs.docker.com/engine/security/)
- [Kubernetes Production Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [FastAPI Performance](https://fastapi.tiangolo.com/deployment/concepts/)
- [PostgreSQL High Performance](https://www.postgresql.org/docs/current/performance-tips.html)

---

**Última atualização:** Outubro 2025  
**Próxima revisão:** Janeiro 2026
