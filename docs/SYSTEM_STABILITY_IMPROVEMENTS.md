# Melhorias de Estabilidade do Sistema

## Problemas Identificados

### 🔴 Críticos

1. **Disco em 81% de Uso**
   - `/dev/mapper/ubuntu--vg-ubuntu--lv: 29G/38G (81%)`
   - Risco: Download de 10 anos pode falhar se disco encher
   - Impacto: Sistema inteiro pode parar

2. **Imagens Docker Órfãs (~1.8GB)**
   - 4 imagens `<none>` ocupando espaço desnecessário
   - Build cache não otimizado

3. **Sem Health Check no Downloader**
   - Container pode travar silenciosamente
   - Impossível detectar problemas automaticamente

4. **Sem Backup Automático**
   - 10 anos de dados sem backup = risco catastrófico
   - Perda de dados irreversível

### ⚠️ Importantes

5. **Logs Sem Rotação no Downloader**
   - Logs podem crescer indefinidamente
   - Outros containers têm `max-size: 50m, max-file: 5`

6. **Sem Limite de Memória**
   - Container pode consumir toda RAM
   - Causa: memory leak, buffer grande

7. **Monitoramento Incompleto**
   - Prometheus/Grafana rodando mas não monitoram downloader
   - Sem alertas de falhas

## Soluções Implementadas

### 📦 Script Automatizado

**Arquivo**: `scripts/maintenance/system_stability_improvements.sh`

**Uso**:
```bash
# Preview (não executa)
./scripts/maintenance/system_stability_improvements.sh --dry-run

# Aplicar melhorias
sudo ./scripts/maintenance/system_stability_improvements.sh
```

### 1. Limpeza de Disco 🗑️

**Ações**:
- Remove imagens Docker órfãs: `docker image prune -f`
- Remove containers parados: `docker container prune -f`
- Remove volumes não usados: `docker volume prune -f`
- Remove logs >30 dias: `find logs/ -name "*.log" -mtime +30 -delete`

**Ganho Esperado**: ~2-3GB liberados

### 2. Docker Compose Melhorado 🐳

**Arquivo**: `docker/docker-compose.downloader.yml`

**Melhorias Aplicadas**:

```yaml
services:
  dukascopy_downloader:
    # Health check: verifica se checkpoint atualiza
    healthcheck:
      test: |
        python3 -c "
        # Verifica se checkpoint foi atualizado nos últimos 10 min
        # Se não, retorna erro
        "
      interval: 5m
      timeout: 10s
      retries: 3
      start_period: 2m
    
    # Limites de recursos
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512m"
        reservations:
          cpus: "0.5"
          memory: "256m"
    
    # Log rotation
    logging:
      driver: "json-file"
      options:
        max-size: "50m"  # Máx 50MB por arquivo
        max-file: "5"    # Mantém 5 arquivos = 250MB max
```

**Benefícios**:
- ✅ Detecta container travado automaticamente
- ✅ Previne consumo excessivo de RAM (limite 512MB)
- ✅ Logs não crescem indefinidamente (máx 250MB)

### 3. Backup Automático 💾

**Arquivo**: `scripts/maintenance/backup_database.sh`

**Funcionamento**:
```bash
# Backup diário às 03:00 (crontab)
0 3 * * * /path/to/backup_database.sh

# O que faz:
# 1. pg_dump do banco mt5_trading
# 2. Compacta com gzip
# 3. Salva em backups/mt5_trading_YYYYMMDD_HHMMSS.sql.gz
# 4. Mantém apenas últimos 7 backups
```

**Comandos**:
```bash
# Backup manual
./scripts/maintenance/backup_database.sh

# Listar backups
ls -lh backups/mt5_trading_*.sql.gz

# Restaurar backup
gunzip < backups/mt5_trading_20251115_030000.sql.gz | \
  docker exec -i mt5_db psql -U trader -d mt5_trading
```

**Benefícios**:
- ✅ Proteção contra perda de dados
- ✅ Ponto de restauração diário
- ✅ Compactado (~10x menor)

### 4. Monitoramento Ativo 📊

**Arquivo**: `scripts/maintenance/monitor_downloader.sh`

**Funcionamento**:
```bash
# Executa a cada 15 minutos (crontab)
*/15 * * * * /path/to/monitor_downloader.sh

# O que verifica:
# 1. Container rodando? Se não, reinicia
# 2. Checkpoint atualizando? Se não (>15min), reinicia
# 3. Uso de memória excessivo? Alerta
```

**Lógica de Auto-Recuperação**:
```bash
# Se checkpoint parado >15 minutos
if [ $DIFF -gt 900 ]; then
    echo "⚠️ Checkpoint travado! Reiniciando..."
    docker-compose restart dukascopy_downloader
fi
```

**Benefícios**:
- ✅ Detecção proativa de problemas
- ✅ Auto-restart em caso de travamento
- ✅ Log de todas verificações

### 5. Alertas Prometheus 🚨

**Arquivo**: `prometheus_rules/downloader_alerts.yml`

**Regras de Alerta**:

```yaml
groups:
  - name: downloader_alerts
    rules:
      # Container parado >2 minutos
      - alert: DownloaderContainerDown
        expr: absent(container_last_seen{name="dukascopy_downloader"}) == 1
        for: 2m
        severity: critical
      
      # Memória >90% por 5 minutos
      - alert: DownloaderHighMemory
        expr: memory_usage > 0.9
        for: 5m
        severity: warning
      
      # Disco <10% livre
      - alert: DiskSpaceLow
        expr: disk_available < 0.1
        for: 5m
        severity: critical
      
      # PostgreSQL down
      - alert: DatabaseDown
        expr: pg_up == 0
        for: 1m
        severity: critical
```

**Integração**:
```yaml
# prometheus.yml
rule_files:
  - 'prometheus_rules/*.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

**Benefícios**:
- ✅ Notificação imediata de problemas
- ✅ Histórico de incidentes
- ✅ Integração com Grafana

## Aplicação das Melhorias

### Passo 1: Executar Script Principal

```bash
cd /home/lair/MT5-Process-Core

# Preview (recomendado)
./scripts/maintenance/system_stability_improvements.sh --dry-run

# Aplicar
sudo ./scripts/maintenance/system_stability_improvements.sh
```

### Passo 2: Verificar Aplicação

```bash
# 1. Container com health check
docker inspect dukascopy_downloader | jq '.[0].State.Health'

# Output esperado:
# {
#   "Status": "healthy",
#   "FailingStreak": 0,
#   "Log": [...]
# }

# 2. Limites de recursos aplicados
docker stats dukascopy_downloader --no-stream

# Output esperado:
# MEM USAGE / LIMIT: 100MB / 512MB

# 3. Crontab configurado
crontab -l | grep -E 'backup|monitor'

# Output esperado:
# 0 3 * * * .../backup_database.sh
# */15 * * * * .../monitor_downloader.sh

# 4. Espaço liberado
df -h / | grep mapper

# Output esperado:
# 29G -> 27G (liberou 2GB)
```

### Passo 3: Testar Backup

```bash
# Executar backup manual
./scripts/maintenance/backup_database.sh

# Verificar arquivo criado
ls -lh backups/

# Output esperado:
# mt5_trading_20251115_HHMMSS.sql.gz  (~50-100MB)
```

### Passo 4: Testar Monitoramento

```bash
# Executar monitor manual
./scripts/maintenance/monitor_downloader.sh

# Output esperado:
# ✅ Container rodando
# 📅 Última data processada: 2015-11-20
# 🕒 Última atualização: 2025-11-15T16:45:00
# 💾 Uso de memória: 120MB / 512MB
```

## Comandos Úteis

### Monitoramento

```bash
# Status geral
docker ps | grep downloader

# Health check
docker inspect dukascopy_downloader | jq '.[0].State.Health.Status'

# Uso de recursos
docker stats dukascopy_downloader --no-stream

# Logs
docker logs -f dukascopy_downloader

# Checkpoint atual
docker exec dukascopy_downloader cat /app/data/checkpoint.json | jq
```

### Backup

```bash
# Backup manual
./scripts/maintenance/backup_database.sh

# Listar backups
ls -lht backups/ | head -10

# Restaurar backup específico
gunzip < backups/mt5_trading_20251115_030000.sql.gz | \
  docker exec -i mt5_db psql -U trader -d mt5_trading

# Verificar tamanho do banco
docker exec mt5_db psql -U trader -d mt5_trading -c "\l+"
```

### Manutenção

```bash
# Limpeza manual
docker system prune -a --volumes  # CUIDADO: remove tudo não usado

# Ver espaço usado
docker system df -v

# Remover imagem específica
docker rmi <image_id>

# Reiniciar downloader
docker-compose -f docker/docker-compose.downloader.yml restart
```

## Checklist de Estabilidade

### Diário
- [ ] Verificar logs do downloader: `./scripts/data/manage_downloader.sh logs`
- [ ] Verificar progresso: `./scripts/data/manage_downloader.sh status`
- [ ] Verificar espaço em disco: `df -h /`

### Semanal
- [ ] Revisar backups: `ls -lh backups/`
- [ ] Verificar logs de erro: `grep -i error logs/*.log`
- [ ] Limpar imagens órfãs: `docker image prune -f`

### Mensal
- [ ] Testar restore de backup
- [ ] Revisar alertas do Prometheus
- [ ] Atualizar dependências: `pip list --outdated`

## Métricas de Sucesso

### Antes das Melhorias
- ❌ Disco: 81% usado (29G/38G)
- ❌ Imagens órfãs: ~1.8GB
- ❌ Sem health check
- ❌ Sem backup automático
- ❌ Sem monitoramento ativo
- ❌ Logs sem limite

### Depois das Melhorias
- ✅ Disco: <75% usado (~27G/38G)
- ✅ Imagens órfãs: 0
- ✅ Health check: a cada 5 minutos
- ✅ Backup: diário às 03:00
- ✅ Monitoramento: a cada 15 minutos
- ✅ Logs: max 250MB (50MB x 5 arquivos)
- ✅ Limites: 1 CPU, 512MB RAM
- ✅ Alertas: 4 regras críticas

### SLA Target
- **Uptime**: >99.5% (máx 3.6h downtime/mês)
- **Recovery Time**: <15 minutos (auto-restart)
- **Data Loss**: 0 (backup diário)
- **Disk Usage**: <80%
- **Memory Usage**: <90% do limite

## Problemas Conhecidos e Workarounds

### 1. Health Check Falso Positivo
**Sintoma**: Container marcado como unhealthy mas está funcionando

**Causa**: Checkpoint não foi criado ainda (primeiros minutos)

**Workaround**: `start_period: 2m` dá tempo para criar checkpoint

### 2. Backup Muito Grande
**Sintoma**: Backup >1GB, lento para criar

**Causa**: 10 anos de dados + índices

**Solução**:
```bash
# Backup apenas schema (rápido)
docker exec mt5_db pg_dump -U trader -d mt5_trading --schema-only > schema.sql

# Backup apenas dados recentes
docker exec mt5_db pg_dump -U trader -d mt5_trading \
  --table=market_data \
  --where="ts > '2024-01-01'" > recent.sql
```

### 3. Monitor Reiniciando Muito
**Sintoma**: Container reinicia a cada 15 minutos

**Causa**: Threshold muito agressivo (15min)

**Solução**: Aumentar para 30min em `monitor_downloader.sh`:
```bash
if [ $DIFF -gt 1800 ]; then  # 30 minutos
```

## Próximos Passos (Futuro)

### Fase 2 - Redundância
- [ ] PostgreSQL replica (streaming replication)
- [ ] Backup off-site (S3/GCS)
- [ ] Load balancer para API

### Fase 3 - Observabilidade Avançada
- [ ] Tracing distribuído (Jaeger integrado)
- [ ] APM (Application Performance Monitoring)
- [ ] Log aggregation (ELK stack)

### Fase 4 - Alta Disponibilidade
- [ ] Multi-region deployment
- [ ] Failover automático
- [ ] Circuit breaker pattern

---

**Última atualização**: 2025-11-15  
**Autor**: ByteLair DevOps Team  
**Status**: Pronto para aplicação  
**Prioridade**: 🔴 Alta (aplicar antes do download completar)
