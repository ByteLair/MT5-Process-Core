# 🔄 Forex Data Updater Container

Container dedicado para **atualização automática** de dados Forex no banco de dados TimescaleDB.

## 📋 Características

- ✅ **Atualização automática** a cada 6 horas
- ✅ **Detecção inteligente** do último candle no banco
- ✅ **Download incremental** apenas de dados novos
- ✅ **Prevenção de duplicatas** (ON CONFLICT)
- ✅ **Retry logic** com backoff exponencial
- ✅ **Healthcheck** integrado
- ✅ **Logs persistentes** em volume Docker
- ✅ **Zero configuração** manual

---

## 🚀 Como Usar

### 1. Build e Start do Container

```bash
# Build da imagem
docker-compose build forex-updater

# Iniciar o container
docker-compose up -d forex-updater

# Verificar logs
docker-compose logs -f forex-updater
```

### 2. Verificar Status

```bash
# Status do container
docker ps | grep forex-updater

# Healthcheck
docker inspect mt5_forex_updater | grep Health -A 10

# Logs em tempo real
docker exec mt5_forex_updater tail -f /var/log/forex-updater/update.log
```

### 3. Executar Atualização Manual

```bash
# Forçar atualização imediata (sem aguardar cron)
docker exec mt5_forex_updater python /app/scripts/update_forex_data.py
```

---

## ⚙️ Configuração

### Variáveis de Ambiente

Configure no `docker-compose.yml`:

```yaml
environment:
  - DB_HOST=db                    # Host do PostgreSQL
  - DB_PORT=5432                  # Porta do PostgreSQL
  - DB_NAME=mt5_trading           # Nome do banco
  - DB_USER=trader                # Usuário
  - DB_PASS=trader123             # Senha
  - FOREX_SYMBOL=EURUSD           # Símbolo a atualizar
  - FOREX_TIMEFRAME=M1            # Timeframe (M1, M5, H1, etc)
  - MAX_RETRIES=3                 # Tentativas em caso de erro
  - RETRY_DELAY=60                # Delay entre tentativas (segundos)
  - TZ=America/Sao_Paulo          # Timezone
```

### Schedule do Cron

Configurado em `docker/updater/crontab`:

| Tarefa | Frequência | Horário |
|--------|-----------|---------|
| **Atualização de dados** | A cada 6 horas | 00:00, 06:00, 12:00, 18:00 |
| **Cálculo de indicadores** | 15 min após atualização | 00:15, 06:15, 12:15, 18:15 |
| **Verificação de saúde** | Diário | 03:00 |
| **Limpeza de logs** | Semanal (domingo) | 04:00 |

Para alterar, edite `docker/updater/crontab` e reconstrua:

```bash
docker-compose build forex-updater
docker-compose up -d forex-updater
```

---

## 📊 Como Funciona

```
┌──────────────────────────────────────────────────────┐
│  FLUXO DE ATUALIZAÇÃO AUTOMÁTICA                     │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1️⃣  CRON TRIGGER (a cada 6 horas)                   │
│      ↓                                               │
│  2️⃣  CONSULTA ÚLTIMA TIMESTAMP                       │
│      SELECT MAX(ts) FROM market_data                 │
│      WHERE symbol='EURUSD' AND timeframe='M1'        │
│      ↓                                               │
│  3️⃣  DOWNLOAD VIA YAHOO FINANCE                      │
│      - Apenas candles após última timestamp          │
│      - Máximo 7 dias (limitação da API)             │
│      ↓                                               │
│  4️⃣  INSERÇÃO NO BANCO                               │
│      INSERT ... ON CONFLICT DO NOTHING               │
│      (evita duplicatas automaticamente)              │
│      ↓                                               │
│  5️⃣  ATUALIZAÇÃO DE ESTATÍSTICAS                     │
│      - Total de candles                              │
│      - Período coberto                               │
│      - Cobertura de indicadores                      │
│      ↓                                               │
│  6️⃣  LOG E NOTIFICAÇÃO                               │
│      /var/log/forex-updater/update.log               │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 📝 Logs

### Localização

```bash
# Dentro do container
/var/log/forex-updater/update.log          # Logs de atualização
/var/log/forex-updater/indicators.log      # Logs de indicadores
/var/log/forex-updater/health.log          # Logs de healthcheck
/var/log/forex-updater/cron-heartbeat.log  # Heartbeat do cron

# No host (via volume)
docker volume inspect mt5_forex_updater_logs
```

### Visualizar Logs

```bash
# Últimas 100 linhas
docker exec mt5_forex_updater tail -100 /var/log/forex-updater/update.log

# Monitorar em tempo real
docker exec mt5_forex_updater tail -f /var/log/forex-updater/update.log

# Buscar erros
docker exec mt5_forex_updater grep "ERROR" /var/log/forex-updater/update.log

# Ver estatísticas
docker exec mt5_forex_updater grep "Estatísticas" /var/log/forex-updater/update.log
```

---

## 🔍 Troubleshooting

### Container não inicia

```bash
# Verificar logs de inicialização
docker-compose logs forex-updater

# Verificar se banco está acessível
docker exec mt5_forex_updater pg_isready -h db -p 5432 -U trader
```

### Dados não estão sendo atualizados

```bash
# Verificar se cron está rodando
docker exec mt5_forex_updater ps aux | grep cron

# Ver cron jobs configurados
docker exec mt5_forex_updater crontab -l

# Executar manualmente para debug
docker exec mt5_forex_updater python /app/scripts/update_forex_data.py
```

### Healthcheck falha

```bash
# Executar healthcheck manualmente
docker exec mt5_forex_updater python /app/scripts/healthcheck.py

# Ver último status
docker inspect mt5_forex_updater | grep -A 20 Health
```

### Limpar logs antigos

```bash
# Manualmente (remove logs com +30 dias)
docker exec mt5_forex_updater find /var/log/forex-updater -name "*.log" -mtime +30 -delete

# Ou reiniciar container (logs persistem no volume)
docker-compose restart forex-updater
```

---

## 🎯 Métricas e Monitoramento

### Prometheus Metrics (futuro)

O container expõe métricas via `/metrics`:

- `forex_updater_last_update_timestamp` - Última atualização
- `forex_updater_candles_inserted_total` - Total de candles inseridos
- `forex_updater_errors_total` - Total de erros
- `forex_updater_update_duration_seconds` - Duração da atualização

### Grafana Dashboard

Importe o dashboard em `grafana/dashboards/forex-updater.json`

---

## 📦 Estrutura de Arquivos

```
docker/updater/
├── Dockerfile                    # Imagem do container
├── requirements-updater.txt      # Dependências Python
├── crontab                       # Configuração do cron
└── entrypoint.sh                 # Script de inicialização

scripts/updater/
├── update_forex_data.py          # Script principal de atualização
├── healthcheck.py                # Script de healthcheck
└── calculate_indicators_incremental.py  # Cálculo incremental (futuro)
```

---

## 🚀 Próximas Melhorias

- [ ] Cálculo incremental de indicadores (apenas novos candles)
- [ ] Suporte a múltiplos símbolos simultâneos
- [ ] WebSocket para dados real-time
- [ ] Notificações via Slack/Discord em caso de erro
- [ ] Métricas Prometheus
- [ ] Dashboard Grafana dedicado
- [ ] Backup automático antes de atualizar
- [ ] Validação de qualidade dos dados (gaps, outliers)

---

## 📚 Documentação Relacionada

- [Guia de Atualização Contínua](../../docs/guides/ATUALIZACAO_DADOS_CONSTANTE.md)
- [Coleta de Dados Históricos](../../docs/guides/COLETA_DADOS_HISTORICOS.md)
- [Estrutura do Banco de Dados](../../docs/database/SCHEMA.md)

---

## 💡 Dicas

1. **Primeira execução**: O container executa uma atualização imediata ao iniciar
2. **Yahoo Finance**: Limitado a 7 dias para M1, suficiente para manter atualizado
3. **Histórico completo**: Use MetaTrader 5 para download inicial de anos
4. **Performance**: Container usa apenas 256MB RAM e 0.5 CPU
5. **Logs**: Rotação automática mantém apenas últimos 30 dias

---

## 📞 Suporte

Para problemas ou sugestões:
- 📧 Issues no GitHub
- 📝 Documentação: `docs/guides/`
- 🔍 Logs: `/var/log/forex-updater/`
