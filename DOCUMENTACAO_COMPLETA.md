# DOCUMENTAÇÃO COMPLETA - MT5 Trading DB

---

## Visão Geral

Este projeto é uma stack para ingestão, armazenamento, análise e automação de sinais de trading com MetaTrader 5, TimescaleDB, FastAPI, ML e automações. Inclui orquestração via Docker, scripts de manutenção, monitoramento, e integração com Prometheus/Grafana.

---

## Estrutura de Diretórios

### Raiz
- `.env`, `.env.example`, `.env.local`: Variáveis de ambiente para containers e serviços
- `docker-compose.yml`, `docker-compose.override.yml`: Orquestração dos serviços
- `Makefile`: Atalhos para operação e desenvolvimento
- `README.md`: Guia rápido do projeto
- `CONTRACTS.md`: Contratos de API, banco e integrações
- `LOG_OPERACIONAL_AI.md`: Registro de ações e troubleshooting
- `openapi.yaml`: Especificação OpenAPI da API
- `requirements-ml.txt`: Dependências agregadas de ML
- `dados_historicos.csv`: Amostra de dados históricos
- `symbol`, `timeframe`: Listas auxiliares de símbolos/timeframes

### `api/`
- `Dockerfile`: Imagem da API FastAPI
- `requirements.txt`, `requirements.lock`: Dependências Python
- `main_patch.txt`: Instruções de patch/middleware
- `app/`: Código principal da API
  - `main.py`: Inicialização FastAPI, routers
  - `ingest.py`: Endpoint `/ingest` para candles
  - `signals.py`: Endpoints de sinais (`/signals/next`, `/signals/ack`)
  - `predict.py`, `predict_batch.py`: Previsão on-demand/batch
  - `metrics.py`, `models.py`: Métricas e modelos
  - `features_sql.py`: SQLs auxiliares para features
  - `worker/`: Workers (ex.: `train.py`)
  - `middleware_auth.py`: Middleware de autenticação/rate limit
  - `config.py`, `session.py`, `utils.py`, `symbols.py`, `latest.py`, `query.py`, `scheduler.py`, `worker.py`, `backtest.py`: Utilidades, consultas, backtest, schedulers
  - `logs/`: Logging específico
  - `models/`: Artefatos ML
  - `data_raw/`: Dados brutos
  - `test.http`: Exemplos de chamadas HTTP

### `db/`
- `init/`: Scripts SQL de inicialização
  - `01-init.sql`: Criação de banco, schemas, tabelas
  - `01-trade_logs.sql`: Estruturas de logs de trade
  - `02-features.sql`, `02-ml.sql`, `02-trade-logs.sql`: Features, ML, logs
  - `03-roles.sql`: Papéis e permissões
  - `20-signals.sql`: Fila de sinais e acks

### `docker/`
- `postgres.conf.d/`: Configuração do Postgres
- `logrotate/`: Regras de logrotate para containers
- `daemon.json`: Configuração do Docker daemon

### `docs/`
- `db_maintenance.md`: Procedimentos de manutenção do banco
- `logging.md`: Padrões de logging
- `cron_example.txt`: Exemplos de crontab
- `structure.md`: Documentação detalhada da estrutura
- `observabilidade.md`: Monitoramento e métricas
- `logging.md`: Logging e troubleshooting

### `ml/`
- `Dockerfile`: Imagem base para ML
- `requirements.txt`, `requirements-ml.txt`, `requirements.lock`: Dependências ML
- Scripts principais:
  - `prepare_dataset.py`: Geração de dataset a partir do banco
  - `train_model.py`, `train_worker.py`: Treino de modelos
  - `scheduler.py`: Scheduler de inferência
  - `eval_threshold.py`: Avaliação de thresholds
- Diretórios:
  - `data/`: Datasets e artefatos
  - `models/`: Modelos treinados
  - `worker/`: Workers auxiliares

### `models/`
- Artefatos de modelo para API/ML (ex.: `latest_model.pkl`)

### `scripts/`
- Scripts de operação/manutenção:
  - `backup.sh`, `pg_backup.sh`, `restore.sh`: Backup/restore do banco
  - `db_maintenance.sh`, `maintenance/restart-docker.sh`: Manutenção
  - `setup_infrastructure.sh`, `setup_docker_permissions.sh`: Infraestrutura
  - `smoke_ingest.sh`, `smoke_query.sh`, `smoke_test_single.sh`, `smoke_test_bulk.sh`: Testes rápidos de API
  - `monitor_backups.sh`, `mt5_backup.sh`, `health_unhealthy_check.sh`: Monitoramento/backup/saúde
  - `tune_postgres_memory.sh`, `otimizacao_market_data.sql`: Tuning
  - `import_csv.py`: Importador de CSV
  - `monitor_ingest_realtime.sh`, `test_ea_simulation.sh`: Monitoramento e simulação de ingestão

### `sql/`
- `features_labels.sql`: SQLs de features/labels para ML

### `systemd/`
- Serviços/timers para orquestração em Linux
  - `mt5-api.service`, `mt5-compose.service`: Inicialização da API/stack
  - `mt5-healthcheck.service`, `mt5-healthcheck.timer`: Healthchecks
  - `mt5-scheduler.service`: Scheduler

### `data/`, `volumes/`, `logs/`, `logrotate.d/`
- Dados locais, volumes persistentes, logs e regras de rotação

### Outros
- `env/`, `env.template`: Templates de variáveis de ambiente
- `ssh/`: Chaves SSH (deploy/backup)
- `init-scripts/`: Scripts suplementares
- `symbol`, `timeframe`: Listas auxiliares

---

## Serviços e Orquestração

- **db**: TimescaleDB/Postgres, armazena candles, features, sinais, logs
- **api**: FastAPI, expõe endpoints REST para ingestão, sinais, métricas, etc
- **ml-trainer**: Prepara dataset e treina modelos
- **ml-scheduler**: Executa inferência periódica e injeta sinais
- **pgadmin**: UI para administração do banco
- **prometheus/grafana**: Monitoramento e dashboards

---

## Endpoints Principais da API

- `/health`: Status da API
- `/ingest`: Recebe candles (single ou batch)
- `/signals/latest`: Últimos sinais gerados
- `/signals/ack`: Confirmação de execução de sinais
- `/predict`: Previsão para símbolo/timeframe
- `/metrics`: Métricas de ingestão/modelos
- `/query`: Consulta tabelas/views whitelisted

**Autenticação:**
- Header obrigatório: `X-API-Key: <chave>`
- CORS controlado por `ALLOW_ORIGINS`

---

## Banco de Dados

- Tabela principal: `public.market_data(symbol, timeframe, ts)`
- Views: `features_m1`, `labels_m1`, `trainset_m1`
- Tabela de saída: `public.signals`, `model_signals`, `signals_queue`, `signals_ack`
- Roles: `mt5_app` (mínimos privilégios)
- Scripts de inicialização em `db/init/`

---

## ML e Automação

- **prepare_dataset.py**: Gera dataset de treino a partir de candles
- **train_model.py**: Treina modelo (RandomForest, etc) e salva em `/models/`
- **scheduler.py**: Executa modelo periodicamente, gera sinais e insere no banco
- **eval_threshold.py**: Avalia thresholds de decisão
- **ml-trainer/ml-scheduler**: Containers dedicados para treino/inferência

---

## Observabilidade

- **Prometheus**: Coleta métricas da API e containers
- **Grafana**: Dashboards para visualização
- **monitor_ingest_realtime.sh**: Monitoramento em tempo real da ingestão

---

## Infraestrutura

- **Docker Compose**: Orquestração dos serviços
- **Systemd**: Serviços/timers para automação em Linux
- **Terraform**: Estrutura inicial para provisionamento cloud

---

## Convenções e Segurança

- Autenticação por API Key
- SQL seguro via SQLAlchemy com parâmetros nomeados
- Operações críticas usam transações
- Logging detalhado e rotacionado
- Permissões mínimas para roles do banco

---

## Fluxo dos Serviços

1. **Ingestão**: EA/Script envia candles via `/ingest` → `market_data`
2. **Features**: Views/tabelas geram features para ML
3. **Treino**: ML trainer prepara dataset e treina modelo
4. **Inferência**: Scheduler executa modelo e insere sinais
5. **Consumo**: API entrega sinais para EA/serviços externos
6. **Monitoramento**: Prometheus/Grafana coletam métricas

---

## Dicas de Operação

- Subir stack: `make up` ou `docker-compose up -d`
- Verificar status: `make ps` ou `docker-compose ps`
- Logs: `make logs` ou `docker-compose logs`
- Testar ingestão: `smoke_ingest.sh` ou curl manual
- Monitorar ingestão: `monitor_ingest_realtime.sh`
- Backup/restore: `backup.sh`, `restore.sh`
- Tuning: `tune_postgres_memory.sh`, `otimizacao_market_data.sql`

---

## Referências Rápidas

- [docs/structure.md](docs/structure.md): Estrutura detalhada
- [CONTRACTS.md](CONTRACTS.md): Contratos de API/banco
- [LOG_OPERACIONAL_AI.md](LOG_OPERACIONAL_AI.md): Troubleshooting
- [observabilidade.md](docs/observabilidade.md): Monitoramento
- [db_maintenance.md](docs/db_maintenance.md): Manutenção do banco

---

**Para dúvidas, onboarding ou troubleshooting, consulte este arquivo e os guias específicos nas pastas `docs/` e scripts em `scripts/`.**
