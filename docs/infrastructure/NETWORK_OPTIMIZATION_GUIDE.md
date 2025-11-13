# MT5 Trading Platform - Network Optimization Guide

## 📡 Visão Geral

Este guia documenta todas as otimizações de rede implementadas para garantir conexão estável mesmo sob carga máxima.

---

## 🔧 Ferramentas de Diagnóstico

### 1. Health Check Completo
```bash
./network_health_check.sh
```

**Funcionalidades:**
- ✅ Verifica configuração de rede Docker
- ✅ Status de containers e saúde
- ✅ Conectividade inter-container
- ✅ Pool de conexões do banco de dados
- ✅ Status do PgBouncer
- ✅ Métricas de performance de rede
- ✅ Tempos de resposta da API
- ✅ Estados de conexões TCP
- ✅ Performance de resolução DNS
- ✅ Uso de recursos de rede

**Saída:** 
- Relatório completo no terminal
- Log detalhado em `logs/network_health_YYYYMMDD_HHMMSS.log`

### 2. Teste de Carga de Rede
```bash
# Teste padrão (5 minutos, 100 requisições concorrentes)
./network_load_test.sh

# Teste customizado
./network_load_test.sh <duração_segundos> <requisições_concorrentes> <endpoint>

# Exemplo: 10 minutos, 200 requisições concorrentes
./network_load_test.sh 600 200 http://localhost:18003/health
```

**Funcionalidades:**
- ✅ Teste de carga com requisições concorrentes
- ✅ Medição de latência (min, max, avg, P50, P90, P95, P99)
- ✅ Taxa de sucesso/falha
- ✅ Throughput de rede (Mbps)
- ✅ Monitoramento de conexões DB durante teste
- ✅ Detecção de erros e packet drops
- ✅ Verificação de saúde pós-teste

**Saída:**
- Resultados detalhados no terminal
- Log em `logs/network_load_test_YYYYMMDD_HHMMSS.log`
- CSV com métricas em `logs/network_load_results_YYYYMMDD_HHMMSS.csv`

### 3. Monitor Contínuo em Tempo Real
```bash
# Monitor com intervalo padrão (5 segundos)
./network_monitor.sh

# Monitor com intervalo customizado
./network_monitor.sh 10  # Atualiza a cada 10 segundos
```

**Funcionalidades:**
- ✅ Dashboard em tempo real no terminal
- ✅ Throughput de rede (RX/TX em Mbps)
- ✅ Contadores de pacotes e erros
- ✅ Latência da API com alertas
- ✅ Uso de conexões do banco de dados
- ✅ Status de saúde dos containers
- ✅ Estatísticas cumulativas
- ✅ Alertas automáticos para anomalias

**Alertas:**
- 🔴 **ERROR**: Falha de health check, containers parados, alta utilização de DB
- 🟡 **WARN**: Latência alta, erros de rede, packet drops
- 🟢 **INFO**: Eventos normais do sistema

---

## 🌐 Configurações de Rede Docker

### Network Settings (docker-compose.yml)
```yaml
networks:
  default:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.name: br-mt5
      com.docker.network.bridge.enable_icc: "true"  # Inter-container communication
      com.docker.network.bridge.enable_ip_masquerade: "true"
      com.docker.network.driver.mtu: "1500"  # MTU padrão
      com.docker.network.bridge.host_binding_ipv4: "0.0.0.0"
    ipam:
      driver: default
      config:
        - subnet: 172.18.0.0/16
          gateway: 172.18.0.1
```

**Benefícios:**
- ✅ Rede dedicada para comunicação inter-container
- ✅ MTU otimizado para evitar fragmentação
- ✅ Subnet consistente e previsível
- ✅ Comunicação eficiente entre containers

---

## 🏥 Health Checks Otimizados

### Database (PostgreSQL + TimescaleDB)
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U trader -d mt5_trading || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 10
  start_period: 30s  # Tempo para inicialização
```

### PgBouncer (Connection Pooler)
```yaml
healthcheck:
  test: ["CMD-SHELL", "PGPASSWORD=${POSTGRES_PASSWORD} psql -h 127.0.0.1 -p 5432 -U trader -d pgbouncer -c 'SHOW POOLS;' >/dev/null"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 20s
```

### API (FastAPI)
```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -fsS http://localhost:8001/health >/dev/null || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 40s  # Aguarda dependências (DB + PgBouncer)
```

**Benefícios:**
- ✅ `start_period` previne falsos positivos durante inicialização
- ✅ Intervalos frequentes detectam problemas rapidamente
- ✅ Timeouts curtos evitam bloqueios prolongados
- ✅ Retries suficientes para transientes temporários

---

## 🔌 Configurações de Conexão

### PostgreSQL (postgresql.conf)

#### Connections
```properties
listen_addresses = '*'
max_connections = 200
superuser_reserved_connections = 5
idle_in_transaction_session_timeout = 600000  # 10 min
statement_timeout = 0
```

#### TCP Keepalive
```properties
tcp_keepalives_idle = 60      # Inicia keepalive após 60s de inatividade
tcp_keepalives_interval = 10  # Intervalo entre probes
tcp_keepalives_count = 5      # Número de probes antes de desconectar
```

**Benefícios:**
- ✅ Detecta conexões mortas rapidamente
- ✅ Previne acúmulo de conexões idle
- ✅ Libera recursos automaticamente

### PgBouncer (pgbouncer.ini)

#### Connection Pooling
```ini
pool_mode = transaction           # Melhor para cargas variáveis
default_pool_size = 25           # Conexões por database/user
min_pool_size = 10               # Mantém conexões warm
reserve_pool_size = 5            # Para picos de carga
max_db_connections = 50          # Limite total ao PostgreSQL
max_client_conn = 1000           # Suporta muitos clientes
```

#### Timeouts
```ini
server_idle_timeout = 600        # 10 min - fecha conexões idle
server_lifetime = 3600           # 1 hora - recicla conexões antigas
server_connect_timeout = 15      # Timeout para conectar ao DB
query_wait_timeout = 120         # Tempo max esperando por slot
reserve_pool_timeout = 5         # Tempo para alocar reserve pool
```

#### TCP Settings
```ini
so_reuseport = 1                 # Distribui conexões entre workers
tcp_keepalive = 1
tcp_keepidle = 60
tcp_keepintvl = 10
tcp_keepcnt = 5
tcp_user_timeout = 30000         # 30s - detecta conexões mortas
```

**Benefícios:**
- ✅ Transaction pooling maximiza reuso de conexões
- ✅ Reserve pool absorve picos temporários
- ✅ Timeouts agressivos previnem travamentos
- ✅ TCP keepalive mantém conexões saudáveis

### SQLAlchemy (config.py)

#### Com PgBouncer
```python
pool_size = 5                    # Pool pequeno, PgBouncer faz pooling
max_overflow = 10                # Conexões extras para bursts
pool_timeout = 10                # Falha rápido se pool esgotado
pool_recycle = 1800              # 30 min - recicla conexões
pool_pre_ping = True             # Verifica saúde antes de usar
```

#### TCP Keepalive (psycopg)
```python
connect_args = {
    "prepare_threshold": 0,       # Desabilitado para transaction pooling
    "connect_timeout": 10,
    "keepalives": 1,
    "keepalives_idle": 60,
    "keepalives_interval": 10,
    "keepalives_count": 5,
    "application_name": "mt5-trading-api",
}
```

**Benefícios:**
- ✅ `pool_pre_ping` detecta conexões mortas
- ✅ `pool_recycle` previne conexões obsoletas
- ✅ TCP keepalive mantém conexões ativas
- ✅ Timeouts curtos falham rápido

---

## 📊 Métricas e Limites

### Thresholds de Performance

| Métrica | Excelente | Aceitável | Crítico |
|---------|-----------|-----------|---------|
| API Response Time | < 100ms | < 1000ms | > 1000ms |
| DB Connections | < 100 (50%) | < 150 (75%) | > 180 (90%) |
| Success Rate | > 99% | > 95% | < 95% |
| Network Latency | < 10ms | < 50ms | > 50ms |
| Packet Loss | 0% | < 0.1% | > 1% |

### Capacidade Máxima

| Recurso | Limite | Observação |
|---------|--------|------------|
| PostgreSQL max_connections | 200 | Configurado em postgresql.conf |
| PgBouncer max_client_conn | 1000 | Limita clientes totais |
| PgBouncer max_db_connections | 50 | Limita conexões ao PostgreSQL |
| SQLAlchemy pool_size | 5 | Por worker/processo |
| API concurrent requests | ~100 | Testado e validado |

---

## 🚀 Testes de Carga - Resultados Esperados

### Cenário: 5 minutos, 100 requisições concorrentes

**Success Rate:** > 99%
- Total Requests: ~30,000+
- Successful: > 29,700
- Failed: < 300

**Response Times:**
- P50 (Median): < 50ms
- P90: < 100ms
- P95: < 200ms
- P99: < 500ms
- Max: < 2000ms

**Network:**
- Throughput: 10-50 Mbps (dependendo do payload)
- Errors: 0
- Packet Loss: < 0.01%

**Database:**
- Peak Connections: < 100
- Connection Pool Saturation: < 50%
- Query Time P95: < 100ms

---

## 🛠️ Troubleshooting

### Problema: Alta Latência

**Sintomas:**
- Response time > 1000ms
- P95 > 500ms

**Diagnóstico:**
```bash
# Verificar conexões DB
docker exec mt5_db psql -U trader -d mt5_trading -c "
  SELECT state, count(*), avg(now() - state_change) 
  FROM pg_stat_activity 
  GROUP BY state;"

# Verificar PgBouncer
docker exec mt5_pgbouncer psql -h 127.0.0.1 -p 5432 -U trader -d pgbouncer -c "SHOW POOLS;"

# Verificar queries lentas
docker exec mt5_db psql -U trader -d mt5_trading -c "
  SELECT query, calls, mean_exec_time, max_exec_time 
  FROM pg_stat_statements 
  ORDER BY mean_exec_time DESC 
  LIMIT 10;"
```

**Soluções:**
1. Aumentar `pool_size` no PgBouncer
2. Adicionar índices no banco de dados
3. Otimizar queries lentas
4. Aumentar recursos (CPU/RAM) se saturados

### Problema: Conexões Esgotadas

**Sintomas:**
- DB connections > 180
- Erros "connection pool exhausted"
- Timeouts frequentes

**Diagnóstico:**
```bash
# Ver conexões por aplicação
docker exec mt5_db psql -U trader -d mt5_trading -c "
  SELECT application_name, state, count(*) 
  FROM pg_stat_activity 
  GROUP BY application_name, state 
  ORDER BY count DESC;"

# Ver conexões idle antigas
docker exec mt5_db psql -U trader -d mt5_trading -c "
  SELECT pid, usename, application_name, state, 
         now() - state_change as duration 
  FROM pg_stat_activity 
  WHERE state = 'idle' 
  ORDER BY duration DESC;"
```

**Soluções:**
1. Aumentar `max_db_connections` no PgBouncer
2. Reduzir `server_idle_timeout` para reciclar mais rápido
3. Verificar connection leaks na aplicação
4. Aumentar `max_connections` no PostgreSQL

### Problema: Packet Loss

**Sintomas:**
- RX/TX dropped > 100
- Network errors > 0
- Conexões instáveis

**Diagnóstico:**
```bash
# Verificar interface Docker
ip -s link show | grep -A5 br-mt5

# Verificar buffer sizes
sysctl net.core.rmem_max
sysctl net.core.wmem_max

# Verificar ring buffer
ethtool -g eth0 2>/dev/null || echo "N/A"
```

**Soluções:**
1. Aumentar buffers de rede:
```bash
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.core.wmem_max=134217728
```

2. Ajustar MTU se necessário
3. Verificar sobrecarga de CPU
4. Considerar usar `host` network mode para serviços críticos

### Problema: DNS Resolution Lento

**Sintomas:**
- DNS lookups > 100ms
- Timeouts intermitentes
- Erros "could not resolve host"

**Diagnóstico:**
```bash
# Testar DNS resolution
docker exec mt5_api time nslookup db

# Verificar configuração DNS
docker exec mt5_api cat /etc/resolv.conf

# Verificar logs DNS
docker logs mt5_api 2>&1 | grep -i "dns\|resolve"
```

**Soluções:**
1. Usar IPs fixos no docker-compose.yml
2. Configurar DNS alternativo
3. Adicionar entradas em `/etc/hosts` dentro dos containers
4. Aumentar `dns_max_ttl` no PgBouncer

---

## 🔍 Monitoramento Contínuo

### Prometheus Metrics

A API expõe métricas em `/prometheus`:

```bash
curl http://localhost:18003/prometheus/
```

**Métricas Importantes:**
- `ingest_candles_inserted_total` - Dados inseridos
- `http_requests_total` - Total de requisições
- `http_request_duration_seconds` - Latência
- `db_connections_active` - Conexões ativas
- `db_query_duration_seconds` - Tempo de queries

### Grafana Dashboards

Acesse: `http://localhost:13000`

**Dashboards Recomendados:**
1. **Network Overview**
   - Throughput (RX/TX)
   - Packet loss
   - Error rates

2. **API Performance**
   - Request rate
   - Response times (P50, P95, P99)
   - Error rate

3. **Database Health**
   - Connection pool usage
   - Query performance
   - Lock contention

4. **Container Health**
   - CPU/Memory usage
   - Network I/O
   - Health check status

---

## 📝 Melhores Práticas

### 1. Health Checks Regulares
```bash
# Executar diariamente
0 6 * * * cd /path/to/MT5-Process-Core && ./network_health_check.sh >> logs/daily_health.log 2>&1
```

### 2. Testes de Carga Semanais
```bash
# Toda segunda-feira às 2 AM
0 2 * * 1 cd /path/to/MT5-Process-Core && ./network_load_test.sh 300 100 >> logs/weekly_load_test.log 2>&1
```

### 3. Monitoramento Contínuo
```bash
# Executar em screen/tmux para persistência
screen -S network-monitor
./network_monitor.sh 10
# Ctrl+A, D para detach
```

### 4. Alertas Automatizados

Integrar com sistemas de alerta (Slack, email, etc):

```bash
# Exemplo: Alertar se health check falhar
if ! ./network_health_check.sh; then
    curl -X POST https://hooks.slack.com/... \
         -d '{"text":"MT5 Network Health Check Failed!"}'
fi
```

### 5. Logs Estruturados

Todos os scripts geram logs em `logs/`:
- `network_health_*.log` - Health checks
- `network_load_test_*.log` - Testes de carga
- `network_load_results_*.csv` - Dados de performance
- `network_monitor_*.log` - Monitoramento contínuo

**Retenção:** Manter últimos 30 dias
```bash
find logs/ -name "*.log" -mtime +30 -delete
find logs/ -name "*.csv" -mtime +30 -delete
```

---

## 🎯 Checklist de Deploy

Antes de colocar em produção:

- [ ] Executar `./network_health_check.sh` - Todos os checks devem passar
- [ ] Executar `./network_load_test.sh 600 200` - Success rate > 99%
- [ ] Verificar configurações de rede no `docker-compose.yml`
- [ ] Confirmar health checks com `start_period` adequado
- [ ] Validar configurações de connection pooling
- [ ] Configurar monitoramento em Grafana
- [ ] Estabelecer alertas para métricas críticas
- [ ] Documentar capacidade máxima testada
- [ ] Criar runbook para incidentes comuns
- [ ] Agendar testes de carga periódicos

---

## 📚 Referências

### Documentação
- [PostgreSQL Connection Settings](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [PgBouncer Configuration](https://www.pgbouncer.org/config.html)
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
- [Docker Networking](https://docs.docker.com/network/)

### Ferramentas
- `docker stats` - Estatísticas de recursos dos containers
- `docker network inspect` - Detalhes da rede Docker
- `ss` / `netstat` - Estado de conexões TCP
- `curl` - Testes de endpoints HTTP
- `psql` - Cliente PostgreSQL

---

## 🔄 Changelog

### 2025-11-12 - Initial Release
- ✅ Script de health check completo
- ✅ Script de teste de carga de rede
- ✅ Monitor em tempo real
- ✅ Otimizações de rede no Docker Compose
- ✅ Health checks com start_period
- ✅ Documentação completa

---

## 📞 Suporte

Para problemas ou dúvidas:
1. Consultar logs em `logs/`
2. Executar `./network_health_check.sh` para diagnóstico
3. Verificar métricas no Grafana
4. Consultar seção de Troubleshooting acima

**Logs Importantes:**
- `logs/network_health_*.log`
- `logs/network_load_test_*.log`
- `docker compose logs <service>`
