# 🌐 MT5 Trading - Network Health & Optimization Tools

> Scripts para garantir conexão estável mesmo em carga máxima

## 🚀 Quick Start

```bash
# 1. Otimizar sistema operacional (executar uma vez, requer sudo)
sudo ./optimize_network.sh

# 2. Verificar saúde da rede
./network_health_check.sh

# 3. Testar sob carga máxima (5 min, 100 req/s)
./network_load_test.sh

# 4. Monitorar em tempo real
./network_monitor.sh
```

## 📋 Scripts Disponíveis

### 1. `optimize_network.sh` ⚙️
**Uso:** `sudo ./optimize_network.sh` (executar uma vez)

Otimiza o sistema operacional Linux para alta performance de rede:
- ✅ Aumenta buffers TCP para 16MB
- ✅ Otimiza backlog de conexões
- ✅ Habilita TCP Fast Open
- ✅ Configura keepalive otimizado
- ✅ Aumenta limites de file descriptors
- ✅ Otimiza configurações Docker
- ✅ Cria backups automáticos

**Quando usar:** Uma vez durante setup inicial ou após reinstalar SO

---

### 2. `network_health_check.sh` 🏥
**Uso:** `./network_health_check.sh`

Verificação completa de saúde da rede e infraestrutura:
- ✅ Configuração de rede Docker
- ✅ Status e saúde dos containers
- ✅ Conectividade inter-container (ping, DNS)
- ✅ Pool de conexões do banco de dados
- ✅ Status do PgBouncer
- ✅ Métricas de interface de rede
- ✅ Tempos de resposta da API
- ✅ Estados de conexões TCP
- ✅ Uso de volumes Docker

**Quando usar:** 
- Diariamente (automatizar via cron)
- Antes de releases
- Ao investigar problemas
- Após mudanças de configuração

**Saída:** Terminal + `logs/network_health_YYYYMMDD_HHMMSS.log`

---

### 3. `network_load_test.sh` 🔥
**Uso:** `./network_load_test.sh [duração] [concorrência] [endpoint]`

Testa estabilidade da rede sob carga máxima:

```bash
# Exemplos
./network_load_test.sh                           # Padrão: 5 min, 100 req/s
./network_load_test.sh 600 200                   # 10 min, 200 req/s
./network_load_test.sh 300 50 http://localhost:18003/docs  # Endpoint customizado
```

**Métricas coletadas:**
- ✅ Taxa de sucesso/falha
- ✅ Latência (min, max, avg, P50, P90, P95, P99)
- ✅ Throughput de rede (Mbps)
- ✅ Pico de conexões DB
- ✅ Packet loss e erros
- ✅ Saúde dos containers durante teste

**Quando usar:**
- Semanalmente (automatizar)
- Antes de releases importantes
- Após otimizações de performance
- Para validar capacidade

**Saída:** 
- Terminal: Resumo e análise
- `logs/network_load_test_*.log`: Log detalhado
- `logs/network_load_results_*.csv`: Dados de performance

---

### 4. `network_monitor.sh` 📊
**Uso:** `./network_monitor.sh [intervalo_segundos]`

Monitor em tempo real com dashboard no terminal:

```bash
./network_monitor.sh     # Atualiza a cada 5s
./network_monitor.sh 10  # Atualiza a cada 10s
```

**Monitora:**
- ✅ Throughput de rede (RX/TX em Mbps)
- ✅ Packets, erros e drops em tempo real
- ✅ Latência da API com alertas
- ✅ Uso de conexões do banco
- ✅ Status de saúde dos containers
- ✅ Estatísticas cumulativas

**Alertas automáticos:**
- 🔴 ERROR: API down, containers parados, DB connections crítico
- 🟡 WARN: Latência alta, erros de rede, packet drops
- 🟢 INFO: Eventos normais

**Quando usar:**
- Durante testes de carga
- Ao investigar problemas em tempo real
- Em ambientes de produção (via screen/tmux)

**Controles:**
- `Ctrl+C` para parar
- Logs salvos em `logs/network_monitor_*.log`

---

## 📊 Thresholds e Limites

| Métrica | Ótimo | Aceitável | Crítico |
|---------|-------|-----------|---------|
| **API Response Time** | < 100ms | < 1000ms | > 1000ms |
| **Success Rate** | > 99% | > 95% | < 95% |
| **DB Connections** | < 100 | < 150 | > 180 |
| **Network Latency** | < 10ms | < 50ms | > 50ms |
| **Packet Loss** | 0% | < 0.1% | > 1% |
| **Network Errors** | 0 | < 10 | > 10 |

## 🔧 Configurações Otimizadas

### Docker Compose (já aplicado)
```yaml
networks:
  default:
    driver: bridge
    driver_opts:
      com.docker.network.bridge.name: br-mt5
      com.docker.network.driver.mtu: "1500"
    ipam:
      config:
        - subnet: 172.18.0.0/16
```

### Health Checks (já aplicado)
- Database: interval=10s, timeout=5s, start_period=30s
- PgBouncer: interval=10s, timeout=5s, start_period=20s
- API: interval=10s, timeout=5s, start_period=40s

### Connection Pooling

**PgBouncer:**
- Pool mode: `transaction`
- Default pool size: `25`
- Max DB connections: `50`
- Max client connections: `1000`

**PostgreSQL:**
- Max connections: `200`
- TCP keepalive: 60s idle, 10s interval, 5 probes

**SQLAlchemy:**
- Pool size: `5` (com PgBouncer)
- Max overflow: `10`
- Pool timeout: `10s`
- Pool recycle: `1800s`
- Pool pre-ping: `true`

## 🔍 Troubleshooting Rápido

### API lenta (latência > 1s)
```bash
# Verificar queries lentas
docker exec mt5_db psql -U trader -d mt5_trading -c "
  SELECT query, mean_exec_time 
  FROM pg_stat_statements 
  ORDER BY mean_exec_time DESC LIMIT 10;"

# Verificar PgBouncer
docker exec mt5_pgbouncer psql -h 127.0.0.1 -p 5432 -U trader -d pgbouncer -c "SHOW POOLS;"
```

### Conexões esgotadas
```bash
# Ver conexões por estado
docker exec mt5_db psql -U trader -d mt5_trading -c "
  SELECT state, count(*) 
  FROM pg_stat_activity 
  GROUP BY state;"

# Matar conexões idle antigas (> 10 min)
docker exec mt5_db psql -U trader -d mt5_trading -c "
  SELECT pg_terminate_backend(pid) 
  FROM pg_stat_activity 
  WHERE state = 'idle' 
    AND state_change < now() - interval '10 minutes';"
```

### Erros de rede
```bash
# Verificar interface Docker
ip -s link show | grep -A5 br-mt5

# Verificar configurações sysctl
sysctl net.ipv4.tcp_rmem
sysctl net.ipv4.tcp_wmem
sysctl net.core.somaxconn

# Re-aplicar otimizações
sudo sysctl -p /etc/sysctl.d/99-mt5-network.conf
```

### Containers não se comunicam
```bash
# Verificar rede Docker
docker network inspect mt5-process-core_default

# Testar DNS
docker exec mt5_api nslookup db

# Testar conectividade
docker exec mt5_api ping -c 3 db

# Reiniciar rede (último recurso)
docker compose down
docker network prune -f
docker compose up -d
```

## 📅 Automação Recomendada

### Crontab
```bash
# Editar crontab
crontab -e

# Adicionar:
# Health check diário às 6 AM
0 6 * * * cd /path/to/MT5-Process-Core && ./network_health_check.sh >> logs/daily_health.log 2>&1

# Teste de carga semanal (segunda-feira 2 AM)
0 2 * * 1 cd /path/to/MT5-Process-Core && ./network_load_test.sh 300 100 >> logs/weekly_load.log 2>&1

# Limpeza de logs antigos (> 30 dias)
0 3 * * 0 find /path/to/MT5-Process-Core/logs -name "*.log" -mtime +30 -delete
```

### Systemd Service (monitor contínuo)
```bash
# Criar /etc/systemd/system/mt5-network-monitor.service
[Unit]
Description=MT5 Network Monitor
After=docker.service

[Service]
Type=simple
User=lair
WorkingDirectory=/home/lair/MT5-Process-Core
ExecStart=/home/lair/MT5-Process-Core/network_monitor.sh 10
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Habilitar e iniciar
sudo systemctl enable mt5-network-monitor
sudo systemctl start mt5-network-monitor
sudo systemctl status mt5-network-monitor
```

## 📈 Grafana Dashboards

Acesse: `http://localhost:13000`

**Queries úteis (Prometheus):**

```promql
# Taxa de requisições API
rate(http_requests_total[5m])

# Latência P95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Conexões DB ativas
db_connections_active

# Throughput de rede (bytes/s)
rate(container_network_receive_bytes_total[5m])
```

## 📚 Documentação Completa

Para detalhes técnicos completos, consulte:
- **[NETWORK_OPTIMIZATION_GUIDE.md](NETWORK_OPTIMIZATION_GUIDE.md)** - Guia completo de otimização

## ✅ Checklist de Deploy

Antes de produção:

- [ ] `sudo ./optimize_network.sh` - Otimizar SO (uma vez)
- [ ] `./network_health_check.sh` - Todos os checks passando
- [ ] `./network_load_test.sh 600 200` - Success rate > 99%
- [ ] Configurar monitoring no Grafana
- [ ] Configurar alertas críticos
- [ ] Agendar health checks automáticos
- [ ] Agendar testes de carga semanais
- [ ] Documentar capacidade máxima testada
- [ ] Criar runbook para incidentes

## 🎯 Resultados Esperados

Após aplicar todas as otimizações:

### Health Check
- ✅ Todos os containers: running + healthy
- ✅ Conectividade inter-container: < 1ms
- ✅ API response time: < 100ms
- ✅ DB connections: < 50% utilização
- ✅ Erros de rede: 0
- ✅ Packet loss: 0%

### Load Test (5 min, 100 req/s)
- ✅ Total requests: ~30,000
- ✅ Success rate: > 99%
- ✅ P50 latency: < 50ms
- ✅ P95 latency: < 200ms
- ✅ P99 latency: < 500ms
- ✅ Peak DB connections: < 100
- ✅ Network errors: 0
- ✅ Packet drops: < 10
- ✅ Throughput: 10-50 Mbps

### Continuous Monitor
- ✅ API uptime: > 99.9%
- ✅ Average latency: < 100ms
- ✅ DB connection usage: < 75%
- ✅ Network errors: 0
- ✅ Container health: all green

## 📞 Suporte

**Logs importantes:**
```bash
# Health checks
tail -f logs/network_health_*.log

# Load tests
tail -f logs/network_load_test_*.log

# Monitor contínuo
tail -f logs/network_monitor_*.log

# Containers
docker compose logs -f api
docker compose logs -f db
```

**Comandos úteis:**
```bash
# Ver todas as redes Docker
docker network ls

# Inspecionar rede MT5
docker network inspect mt5-process-core_default

# Stats em tempo real
docker stats

# Ver configurações aplicadas
sysctl -a | grep net.ipv4.tcp

# Testar endpoint API
curl -w "\nTime: %{time_total}s\n" http://localhost:18003/health
```

---

**Desenvolvido para MT5 Trading Platform** 🚀
**Última atualização:** 2025-11-12
