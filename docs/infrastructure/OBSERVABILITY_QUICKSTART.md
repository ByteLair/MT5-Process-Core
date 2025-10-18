# 🔍 Guia Rápido de Observabilidade

## 🌐 URLs de Acesso

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **Grafana** | http://192.168.15.20:3000 | Dashboards e visualizações<br>👤 `admin` / `admin` |
| **Jaeger UI** | http://192.168.15.20:16686 | Distributed tracing |
| **Prometheus** | http://192.168.15.20:9090 | Métricas time-series |
| **Loki API** | http://192.168.15.20:3100 | API de logs |

## 📊 Dashboards Disponíveis no Grafana

1. **MT5 Trading - Logs (Loki)**
   - Logs centralizados de todos os containers
   - Filtros por job, nível, container
   - Painel de erros em tempo real

2. **Health Check System**
   - Status dos componentes
   - Histórico de checks
   - Alertas ativos

3. **Sistema Metrics** (Prometheus)
   - CPU, memória, disco
   - Requests, latência
   - Database performance

## 🚀 Quick Start

### Ver logs em tempo real

```bash
# No Grafana
1. Acesse: http://192.168.15.20:3000
2. Menu: Explore
3. Selecione datasource: Loki
4. Query: {job="mt5_api"}
```

### Ver traces da API

```bash
# No Jaeger
1. Acesse: http://192.168.15.20:16686
2. Service: mt5-trading-api
3. Operation: Selecione endpoint
4. Clique em "Find Traces"
```

### Queries LogQL Úteis

```logql
# Todos os logs da API
{job="mt5_api"}

# Erros na última hora
{level="ERROR"}

# Logs de um container específico
{container_name="mt5_api"}

# Busca por texto
{job="mt5_api"} |= "signal"

# Erros com trace ID
{job="mt5_api", level="ERROR"} |~ "traceID=\\w+"
```

### Queries PromQL Úteis

```promql
# Taxa de requests
rate(http_requests_total[5m])

# Latência p95
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m])
)

# Uso de memória
container_memory_usage_bytes{container="mt5_api"} / 1024 / 1024
```

## 🔧 Gerenciar Serviços

```bash
# Verificar status
docker ps | grep -E "loki|promtail|jaeger|grafana|prometheus"

# Ver logs
docker logs mt5_loki
docker logs mt5_promtail
docker logs mt5_jaeger

# Reiniciar serviços
docker-compose restart loki promtail jaeger grafana

# Parar serviços
docker-compose stop loki promtail jaeger

# Subir serviços
docker-compose up -d loki promtail jaeger grafana
```

## 📝 Estrutura de Logs

### Loki coleta logs de:

- **Docker Containers**: Todos os containers via JSON logs
- **API MT5**: Logs da aplicação em `/app/logs/*.log`
- **Health Checks**: Sistema de monitoramento em `/app/logs/health-checks/*.log`
- **PostgreSQL**: Logs do banco em `/var/log/postgresql/*.log`
- **Syslog**: Logs do sistema em `/var/log/syslog`

### Jaeger rastreia:

- **Requests HTTP**: Todos os endpoints da API
- **Database Queries**: Queries SQL via SQLAlchemy
- **Custom Spans**: Operações marcadas com `@traced`

## 🐛 Troubleshooting

### Loki não mostra logs

```bash
# Verificar Promtail
docker logs mt5_promtail | tail -20

# Verificar se Loki está pronto
curl http://localhost:3100/ready

# Testar query manual
curl -G http://localhost:3100/loki/api/v1/query \
  --data-urlencode 'query={job="docker"}' \
  --data-urlencode 'limit=10'
```

### Jaeger não mostra traces

```bash
# Verificar health
curl http://localhost:14269/

# Ver logs
docker logs mt5_jaeger | tail -20

# Verificar se API está enviando traces
docker logs mt5_api | grep -i jaeger
```

### Grafana não mostra dados

```bash
# Verificar datasources
curl http://localhost:3000/api/datasources

# Testar Loki
curl http://localhost:3100/ready

# Testar Jaeger
curl http://localhost:16686/api/services
```

## 📚 Documentação Completa

Para documentação detalhada, consulte:
- **OBSERVABILITY_STACK.md**: Guia completo com arquitetura, queries, best practices
- **HEALTH_CHECK_SYSTEM.md**: Sistema de monitoramento e alertas

## 🎯 Casos de Uso Comuns

### 1. Investigar erro na API

```
1. Grafana → Dashboard "MT5 Trading - Logs (Loki)"
2. Painel "⚠️ Logs de Erro"
3. Clicar no log com traceID
4. Abre automaticamente no Jaeger
5. Ver timeline completo da request
```

### 2. Analisar performance

```
1. Jaeger → Service: mt5-trading-api
2. Filtrar: minDuration=1s
3. Analisar spans lentos
4. Ver queries SQL no trace
```

### 3. Monitorar sistema

```
1. Grafana → Dashboard "Health Check System"
2. Ver status de todos componentes
3. Alertas ativos aparecem em vermelho
4. Histórico dos últimos 24h
```

## 🔐 Segurança

**Importante**: Em produção, configure:

1. **Autenticação no Grafana**: Trocar senha padrão
2. **TLS/HTTPS**: Usar reverse proxy (Nginx/Traefik)
3. **Firewall**: Expor apenas Grafana externamente
4. **Jaeger**: Usar autenticação no collector
5. **Loki**: Configurar autenticação multi-tenant

## 📊 Retenção de Dados

| Serviço | Retenção | Localização |
|---------|----------|-------------|
| Loki | 30 dias | Volume `loki_data` |
| Jaeger | Persistente | Volume `jaeger_data` |
| Prometheus | 90 dias | Volume `prometheus_data` |

---

**Última atualização**: 2025-10-18  
**Status**: ✅ Todos os serviços funcionando
