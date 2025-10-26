# MT5 Trading System - Runbook Operacional

Este documento contém procedimentos step-by-step para operações, deploys, rollbacks e resposta a incidentes.

## Índice

1. [Operações Diárias](#operações-diárias)
2. [Deploy](#deploy)
3. [Rollback](#rollback)
4. [Backup e Restore](#backup-e-restore)
5. [Resposta a Incidentes](#resposta-a-incidentes)
6. [Manutenção](#manutenção)
7. [Disaster Recovery](#disaster-recovery)

---

## Operações Diárias

### Checklist Matinal (08:00)

```bash
# 1. Verificar status de todos os serviços
./scripts/health-check.sh

# 2. Verificar alertas Grafana
curl -s http://localhost:3000/api/alerts | jq '.[] | select(.state=="alerting")'

# 3. Verificar logs de erro (últimas 24h)
docker compose logs --since 24h | grep -i "error\|critical\|exception"

# 4. Verificar espaço em disco
df -h | grep -E 'Use%|volumes'

# 5. Verificar métricas principais
curl -s http://localhost:8001/metrics | grep -E "requests_total|error_rate"

# 6. Verificar treinamento ML (último sucesso)
ls -lth ml/models/ | head -5
```

**Ações se algum check falhar:**

- Serviço down → Ver [Resposta a Incidentes](#resposta-a-incidentes)
- Disk > 80% → Ver [Manutenção - Limpeza](#limpeza-de-disco)
- Alertas ativos → Investigar logs e métricas

### Monitoramento Contínuo

**Dashboards principais:**

1. **MT5 Trading Main**: <http://localhost:3000/d/mt5-trading-main>
2. **Infrastructure & Logs**: <http://localhost:3000/d/mt5-infra-logs>
3. **Database Metrics**: <http://localhost:3000/d/mt5-db-dashboard>

**Frequência de verificação:**

- Dashboards: A cada 2 horas
- Email alerts: Imediato (<kuramopr@gmail.com>)
- Daily report: 04:30 (automatizado)

---

## Deploy

### Deploy de Nova Versão da API

#### 1. Preparação

```bash
# Criar branch de release
cd /home/felipe/MT5-Process-Core-full
git checkout -b release/api-v1.2.0

# Atualizar versão
echo "v1.2.0" > api/VERSION

# Commit
git add api/
git commit -m "Release API v1.2.0"
git push origin release/api-v1.2.0
```

#### 2. Build e Test

```bash
# Build nova imagem
docker compose build api

# Executar testes
docker compose run --rm api pytest api/tests/

# Verificar imagem
docker images | grep mt5_api
```

#### 3. Deploy (Blue-Green)

```bash
# 1. Start nova versão em porta alternativa
docker run -d \
  --name mt5_api_new \
  --network mt5_network \
  -p 8002:8000 \
  -e DATABASE_URL=$DATABASE_URL \
  -v ml_models:/models \
  mt5_api:latest

# 2. Healthcheck da nova versão
for i in {1..10}; do
  curl -f http://localhost:8002/health && echo "✓" || echo "✗"
  sleep 2
done

# 3. Se OK, trocar porta (atualizar docker-compose.yml ou proxy)
# Parar versão antiga
docker stop mt5_api

# Renomear nova versão
docker rename mt5_api_new mt5_api

# Ou simplesmente
docker compose up -d api
```

#### 4. Validação Pós-Deploy

```bash
# Verificar logs
docker logs mt5_api --tail 100

# Testar endpoints principais
./scripts/smoke_test.sh

# Monitorar métricas (5 minutos)
watch -n 10 'curl -s http://localhost:8001/metrics | grep requests_total'

# Se tudo OK, merge para main
git checkout main
git merge release/api-v1.2.0
git push origin main
git tag -a v1.2.0 -m "API Release v1.2.0"
git push origin v1.2.0
```

### Deploy de Novo Modelo ML

#### 1. Treinar Novo Modelo

```bash
# Executar treinamento
docker compose exec ml python ml/worker/train.py

# Verificar métricas
cat ml/models/rf_m1_metrics.json
```

#### 2. Validação Offline

```bash
# Backtest do novo modelo
docker compose exec api python -c "
from api.backtest import run_backtest
results = run_backtest(model_path='/models/rf_m1.pkl', days=30)
print(results)
"

# Métricas esperadas:
# - Accuracy > 0.55
# - Precision > 0.60
# - Sharpe Ratio > 1.0
```

#### 3. A/B Testing (Opcional)

```python
# api/predict.py
import random

def get_model_version():
    # 90% usa modelo antigo, 10% usa novo
    if random.random() < 0.1:
        return "rf_m1_new.pkl"
    else:
        return "rf_m1.pkl"
```

#### 4. Rollout Completo

```bash
# Substituir modelo em produção
docker compose exec ml cp /models/rf_m1_new.pkl /models/rf_m1.pkl

# Restart API para reload do modelo
docker compose restart api

# Monitorar performance (30 minutos)
# Verificar Grafana dashboard ML/AI
```

### Deploy de Infraestrutura

#### Atualizar Docker Compose

```bash
# 1. Editar docker-compose.yml
vim docker-compose.yml

# 2. Validar sintaxe
docker compose config

# 3. Preview changes
docker compose up --dry-run

# 4. Apply changes (recreate only modified services)
docker compose up -d

# 5. Verificar status
docker compose ps
```

#### Atualizar Configuração Grafana

```bash
# 1. Editar dashboards/alertas
vim grafana/provisioning/alerting/new-alert.yaml

# 2. Restart Grafana
docker compose restart grafana

# 3. Verificar provisioning
docker logs grafana | grep -i "provisioning"

# 4. Acessar Grafana UI
xdg-open http://localhost:3000
```

---

## Rollback

### Rollback de API

#### Método 1: Revert Docker Image

```bash
# Listar imagens anteriores
docker images | grep mt5_api

# Rollback para versão anterior
docker tag mt5_api:v1.1.0 mt5_api:latest
docker compose up -d api

# Verificar
./scripts/smoke_test.sh
```

#### Método 2: Git Revert

```bash
# Reverter commit
git revert HEAD
docker compose build api
docker compose up -d api
```

#### Método 3: Restore Backup

```bash
# Ver [Backup e Restore](#restore-de-backup)
```

### Rollback de Modelo ML

```bash
# 1. Listar backups de modelos
ls -lth ml/models/backups/

# 2. Restaurar versão anterior
docker compose exec ml cp /models/backups/rf_m1_v1.1.0.pkl /models/rf_m1.pkl

# 3. Restart API
docker compose restart api

# 4. Validar
curl http://localhost:8001/predict?symbol=EURUSD
```

### Rollback de Database Schema

```bash
# 1. Restaurar dump de schema
docker exec -i mt5_db psql -U trader -d mt5_trading < backups/schema_backup_20251018.sql

# 2. Restart serviços dependentes
docker compose restart api ml

# 3. Verificar integridade
docker exec mt5_db psql -U trader -d mt5_trading -c "\dt"
```

---

## Backup e Restore

### Backup Manual

#### Database

```bash
# Full backup (dados + schema)
docker exec mt5_db pg_dump -U trader -F c mt5_trading > \
  backups/mt5_trading_$(date +%Y%m%d_%H%M%S).dump

# Schema only
docker exec mt5_db pg_dump -U trader --schema-only mt5_trading > \
  backups/schema_$(date +%Y%m%d).sql

# Data only (tabela específica)
docker exec mt5_db pg_dump -U trader -t market_data --data-only mt5_trading > \
  backups/market_data_$(date +%Y%m%d).sql
```

#### Modelos ML

```bash
# Backup de modelos
tar -czf backups/models_$(date +%Y%m%d).tar.gz ml/models/

# Backup incremental (apenas novos modelos)
rsync -av --delete ml/models/ backups/models_mirror/
```

#### Configurações

```bash
# Backup de configs
tar -czf backups/configs_$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  grafana/provisioning/ \
  prometheus/prometheus.yml \
  systemd/
```

### Backup Automatizado

```bash
# Executado diariamente às 04:00 via systemd timer
# scripts/remote_backup.sh

# Verificar último backup
ssh backup@100.113.13.126 'ls -lth /backups/mt5-trading/ | head -10'

# Forçar backup manual
./scripts/remote_backup.sh
```

### Restore de Backup

#### Database Full Restore

```bash
# 1. Parar serviços
docker compose stop api ml

# 2. Drop database atual (CUIDADO!)
docker exec mt5_db psql -U trader -c "DROP DATABASE mt5_trading;"
docker exec mt5_db psql -U trader -c "CREATE DATABASE mt5_trading;"

# 3. Restore
docker exec -i mt5_db pg_restore -U trader -d mt5_trading < \
  backups/mt5_trading_20251018_040000.dump

# 4. Restart serviços
docker compose start api ml

# 5. Validar
docker exec mt5_db psql -U trader -d mt5_trading -c "SELECT count(*) FROM market_data;"
```

#### Restore Parcial (Tabela Específica)

```bash
# Restore apenas uma tabela
docker exec -i mt5_db psql -U trader -d mt5_trading -t market_data < \
  backups/market_data_20251018.sql

# Ou via pg_restore
docker exec mt5_db pg_restore -U trader -d mt5_trading -t market_data \
  backups/mt5_trading_20251018.dump
```

#### Restore de Remote Backup

```bash
# 1. Download do backup remoto
scp backup@100.113.13.126:/backups/mt5-trading/mt5_trading_20251018.dump.gz ./

# 2. Descomprimir
gunzip mt5_trading_20251018.dump.gz

# 3. Restore
docker exec -i mt5_db pg_restore -U trader -d mt5_trading < \
  mt5_trading_20251018.dump
```

---

## Resposta a Incidentes

### Incident Response Plan

#### Níveis de Severidade

- **P0 (Critical)**: Sistema completamente inoperante
- **P1 (High)**: Funcionalidade principal degradada
- **P2 (Medium)**: Funcionalidade secundária afetada
- **P3 (Low)**: Issue menor sem impacto nos usuários

#### Workflow de Resposta

```
1. DETECÇÃO
   ↓
2. TRIAGEM (classificar severidade)
   ↓
3. INVESTIGAÇÃO (logs, métricas)
   ↓
4. MITIGAÇÃO (fix temporário)
   ↓
5. RESOLUÇÃO (fix permanente)
   ↓
6. POST-MORTEM (RCA + ações preventivas)
```

### Incidente: API Down (P0)

#### Detecção

```
Alerta Grafana: "API Down"
Email: kuramopr@gmail.com
Métrica: up{job="mt5-api"} == 0
```

#### Investigação

```bash
# 1. Verificar se container está rodando
docker ps | grep mt5_api

# 2. Se não está rodando, verificar logs
docker logs mt5_api --tail 100

# 3. Verificar resources
docker stats mt5_api --no-stream

# 4. Verificar dependências (DB, PgBouncer)
docker ps | grep -E "mt5_db|mt5_pgbouncer"
```

#### Mitigação

```bash
# Tentativa 1: Restart simples
docker compose restart api

# Tentativa 2: Rebuild
docker compose build api
docker compose up -d api

# Tentativa 3: Rollback para versão anterior
docker tag mt5_api:v1.1.0 mt5_api:latest
docker compose up -d api

# Tentativa 4: Restore de backup completo
# (ver seção Restore)
```

#### Resolução

```bash
# Após API voltar, investigar root cause
docker logs mt5_api --since "1 hour ago" > /tmp/api_incident.log

# Análise de logs
grep -E "ERROR|CRITICAL|Exception" /tmp/api_incident.log
```

### Incidente: Database Lento (P1)

#### Detecção

```
Alerta Grafana: "Slow Database Queries"
Métrica: pg_stat_statements_mean_time_ms > 100
```

#### Investigação

```sql
-- Queries ativas
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT pid, query, state, wait_event_type, wait_event
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start;
"

-- Queries mais lentas
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT query, calls, mean_exec_time, max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

-- Locks
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT * FROM pg_locks WHERE NOT granted;
"

-- Cache hit ratio
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS cache_ratio
FROM pg_statio_user_tables;
"
```

#### Mitigação

```bash
# Se há locks, matar query bloqueante
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT pg_terminate_backend(12345);  -- PID da query
"

# Vacuum manual
docker exec mt5_db psql -U trader -d mt5_trading -c "VACUUM ANALYZE market_data;"

# Restart PostgreSQL (last resort)
docker compose restart db
```

### Incidente: Disk Full (P1)

#### Detecção

```
Alerta: Disk usage > 90%
Comando: df -h
```

#### Investigação

```bash
# Verificar uso por volume
docker system df -v

# Encontrar arquivos grandes
du -sh /var/lib/docker/volumes/* | sort -h | tail -20

# Logs grandes
du -sh logs/* | sort -h | tail -10
```

#### Mitigação

```bash
# 1. Limpar logs antigos
find logs/ -name "*.log" -mtime +30 -delete

# 2. Limpar Docker (images, containers, volumes não usados)
docker system prune -af --volumes

# 3. Compressão forçada TimescaleDB (dados > 7 dias)
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT compress_chunk(i)
FROM show_chunks('market_data') i
WHERE range_end < now() - interval '7 days';
"

# 4. Drop dados antigos (> 1 ano)
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT drop_chunks('market_data', older_than => interval '1 year');
"

# 5. Exportar e mover backups para remote
./scripts/remote_backup.sh
rm -rf backups/*
```

### Incidente: Modelo ML com Performance Ruim (P2)

#### Detecção

```
Alerta: ML Model Accuracy < 0.55
Dashboard: ML/AI Metrics
```

#### Investigação

```bash
# Verificar métricas do modelo atual
cat ml/models/rf_m1_metrics.json

# Verificar data drift
docker compose exec ml python -c "
from ml.train_model import check_data_drift
drift = check_data_drift('/models/rf_m1.pkl')
print(drift)
"

# Verificar tamanho do dataset de treino
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT count(*) FROM trainset_m1
WHERE ts >= now() - interval '60 days';
"
```

#### Mitigação

```bash
# 1. Rollback para modelo anterior
docker compose exec ml cp /models/backups/rf_m1_v1.1.0.pkl /models/rf_m1.pkl
docker compose restart api

# 2. Re-treinar com dados mais recentes
docker compose exec ml python ml/worker/train.py

# 3. Ajustar hiperparâmetros
# Editar ml/worker/train.py
# n_estimators, max_depth, etc.
```

---

## Manutenção

### Limpeza de Disco

```bash
# Executar script de manutenção
./scripts/maintenance.sh

# Ou manualmente:

# 1. Logs antigos (> 30 dias)
find logs/ -name "*.log" -mtime +30 -delete

# 2. Docker cleanup
docker system prune -af

# 3. Backup antigos locais (> 7 dias)
find backups/ -mtime +7 -delete

# 4. Compression TimescaleDB
docker exec mt5_db psql -U trader -d mt5_trading -c "
CALL run_job(1);  -- Job ID da compression policy
"
```

### Atualização de Dependências

```bash
# Python (API + ML)
docker compose exec api pip list --outdated
docker compose exec api pip install --upgrade <package>

# Rebuild image
docker compose build api ml
docker compose up -d api ml

# Testar
pytest api/tests/
pytest ml/tests/
```

### Database Maintenance

```bash
# Vacuum e Analyze (semanalmente)
docker exec mt5_db psql -U trader -d mt5_trading -c "
VACUUM ANALYZE;
"

# Reindex (mensalmente)
docker exec mt5_db psql -U trader -d mt5_trading -c "
REINDEX DATABASE mt5_trading;
"

# Verificar bloat
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT
    schemaname || '.' || tablename AS table,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
"
```

---

## Disaster Recovery

### Cenário: Perda Total do Servidor

#### Recovery Steps

```bash
# 1. Provisionar novo servidor
ssh new-server

# 2. Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 3. Clonar repositório
git clone https://github.com/Lysk-dot/mt5-trading-db.git
cd mt5-trading-db

# 4. Configurar .env
cp .env.example .env
vim .env  # Preencher variáveis

# 5. Download backup remoto
scp backup@100.113.13.126:/backups/mt5-trading/latest/* ./backups/

# 6. Restore database
docker compose up -d db
sleep 10
docker exec -i mt5_db pg_restore -U trader -d mt5_trading < backups/mt5_trading_latest.dump

# 7. Restore modelos e configs
tar -xzf backups/models_latest.tar.gz -C ml/
tar -xzf backups/configs_latest.tar.gz

# 8. Start todos os serviços
docker compose up -d

# 9. Verificar
./scripts/health-check.sh

# 10. Re-ativar automações
sudo cp systemd/*.service /etc/systemd/system/
sudo cp systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mt5-update.timer mt5-tests.timer mt5-daily-report.timer
```

**RTO (Recovery Time Objective):** 2 horas
**RPO (Recovery Point Objective):** 24 horas (backup diário)

---

## Contatos de Emergência

```
Tech Lead: kuramopr@gmail.com
DevOps: [...]
Database Admin: [...]
```

---

## Recursos Adicionais

- **Documentação**: `docs/DOCUMENTATION.md`
- **Performance**: `docs/PERFORMANCE.md`
- **Troubleshooting**: `docs/DOCUMENTATION.md#troubleshooting`
- **Grafana Dashboards**: <http://localhost:3000>
- **Prometheus**: <http://localhost:9090>
