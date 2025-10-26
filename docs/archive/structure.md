# Estrutura do Projeto: MT5 Trading DB

Este documento descreve, pasta a pasta, a finalidade de cada componente do repositório, como os serviços interagem e onde encontrar os artefatos principais (banco, API, ML, automações e operações).

> Dica: consulte também o `docker-compose.yml` e o `docker-compose.override.yml` para entender como os serviços são orquestrados.

---

## Raiz do repositório

- `.env` / `.env.example` / `.env.local`:
  - Configurações de ambiente usadas pelos containers (DB, API, portas, etc.).
  - O arquivo `.env` efetivo é carregado pelo docker-compose.
- `docker-compose.yml` e `docker-compose.override.yml`:
  - Orquestração dos serviços: `db` (TimescaleDB/Postgres), `api` (FastAPI), `ml-trainer`, `ml-scheduler`, `pgadmin`.
  - `override` adiciona conveniências (volumes, portas, envs extra) e pode sobrepor comportamentos do compose base.
- `Makefile`:
  - Atalhos para desenvolvimento e operação (ex.: `make up`, `make logs`, `make ps`, `make api-up`).
- `README.md`:
  - Guia geral do projeto, procedimentos de calibração e manutenção.
- `CONTRACTS.md`:
  - Contratos/expectativas entre componentes (por exemplo, formato de eventos, endpoints).
- `LOG_OPERACIONAL_AI.md`:
  - Registro e diretrizes operacionais relacionados à IA/ML.
- `openapi.yaml`:
  - Especificação OpenAPI da API (pode estar parcialmente atualizada; a fonte da verdade é o código FastAPI).
- `requirements-ml.txt` (raiz):
  - Dependências agregadas de ML (podem ser usadas em ambientes locais).
- `dados_historicos.csv` (eventual):
  - Amostra de dados históricos para ingestão/testes.
- `symbol`, `timeframe`:
  - Arquivos/recursos auxiliares (listas de símbolos e timeframes) usados em processos.

## Pasta `api/`

- `Dockerfile`:
  - Imagem da API FastAPI (uvicorn). Instala dependências de `requirements.txt` e copia o código.
- `requirements.txt` / `requirements.lock`:
  - Dependências Python da API (FastAPI, SQLAlchemy, psycopg, etc.).
- `__init__.py`:
  - Torna o diretório um pacote Python.
- `main_patch.txt`:
  - Instruções para aplicar middlewares (CORS, API Key middleware) em `app/main.py` se necessário.
- Código principal:
  - `app/main.py`: cria o app FastAPI, define rotas básicas (`/health`, `/signals/latest`, etc.) e inclui os routers.
  - `app/ingest.py`: endpoint `/ingest` para inserir candles no `market_data` (suporta single e batch `{items: [...]}`).
  - `app/signals.py`: endpoints de sinais (`/signals/next`, `/signals/ack`) e autenticação por API Key.
  - `app/predict.py`, `app/predict_batch.py`: previsão on-demand e em batch (se aplicável ao seu fluxo).
  - `app/metrics.py`, `app/models.py`: métricas e modelos de dados usados pela API.
  - `app/features_sql.py`: consultas/SQL auxiliares para features.
  - `app/worker/`: workers específicos (ex.: `train.py`) que podem ser executados por jobs ou manualmente.
- Utilidades e infraestrutura:
  - `middleware_auth.py`: middleware com API Key + rate limit.
  - `config.py`, `session.py`, `utils.py`, `symbols.py`, `latest.py`, `query.py`, `scheduler.py`, `worker.py`, `backtest.py`:
    - Utilidades de configuração (ENV, conexões), sessões DB, ferramentas de consulta, backtest, schedulers locais.
  - `logs/`: módulos de logging específicos da aplicação.
  - `models/`: artefatos ML que a API pode carregar (ex.: `/models/latest_model.pkl` montado via volume).
  - `data_raw/`: dados brutos que a API pode usar em tarefas auxiliares.
  - `test.http`: exemplos de chamadas HTTP para testar endpoints via REST client.

## Pasta `db/`

- `init/`:
  - Scripts SQL executados automaticamente na inicialização do container do Postgres/Timescale:
    - `01-init.sql`: criação de banco, schemas, tabelas base.
    - `01-trade_logs.sql`: estruturas de logs de trade.
    - `02-features.sql`, `02-ml.sql`, `02-trade-logs.sql`: tabelas, views e índices para features/ML e logs.
    - `03-roles.sql`: papéis/roles e permissões.
    - `20-signals.sql`: estruturas para fila de sinais e acks.

## Pasta `docker/`

- `postgres.conf.d/`: configuração do Postgres (`postgresql.conf`) aplicada via bind mount no serviço `db`.
- `logrotate/`: regras de logrotate específicas para containers/services (ex.: `mt5-containers`).
- `daemon.json`: configuração do Docker daemon (se necessário para tuning local ou servidor).

## Pasta `docs/`

- `db_maintenance.md`:
  - Procedimentos, cron e tuning do banco (compactação, retenção, VACUUM, etc.).
- `logging.md`:
  - Padrões e recomendações de logging do projeto.
- `cron_example.txt`:
  - Exemplos de crontab para automatizações locais.
- `structure.md` (este arquivo):
  - Descrição detalhada da estrutura do repositório.

## Pasta `ml/`

- `Dockerfile`:
  - Imagem base para processos de ML (treino, preparação de dataset, scheduler de inferência).
- `requirements.txt` / `requirements-ml.txt` / `requirements.lock`:
  - Dependências de ML (pandas, scikit-learn, joblib, APScheduler, SQLAlchemy, psycopg, etc.).
- Scripts principais:
  - `prepare_dataset.py`: lê `market_data`, gera features e grava dataset em `ml/data/training_dataset.csv` e `/app/data/dataset.csv` (p/ healthcheck).
  - `train_model.py`: treina modelo (ex.: RandomForest) a partir do dataset e salva em `models/`.
  - `train_worker.py`: alternativa de treino, conectando diretamente ao DB.
  - `scheduler.py`: job que periodicamente lê features e grava sinais em tabelas (usa `APScheduler`).
  - `eval_threshold.py`: avalia thresholds de predição e gera métricas.
- Diretórios:
  - `data/`: datasets e artefatos intermediários gerados.
  - `models/`: modelos treinados (ex.: `latest_model.pkl`).
  - `worker/`: workers auxiliares (ex.: `train.py`).

## Pasta `models/`

- Artefatos de modelo para a API e/ou ML (pasta montada como volume no container). Ex.: `latest_model.pkl`.

## Pasta `scripts/`

- Scripts de operação e manutenção:
  - `backup.sh`, `pg_backup.sh`, `restore.sh`: backup e restore do banco.
  - `db_maintenance.sh`, `maintenance/restart-docker.sh`: tarefas de manutenção do banco e do Docker.
  - `setup_infrastructure.sh`, `setup_docker_permissions.sh`: preparação de infraestrutura local/servidor.
  - `smoke_ingest.sh`, `smoke_query.sh`, `smoke_test_single.sh`, `smoke_test_bulk.sh`: testes rápidos de API.
  - `monitor_backups.sh`, `mt5_backup.sh`, `health_unhealthy_check.sh`: monitoramento e rotinas de backup/saúde.
  - `tune_postgres_memory.sh`, `otimizacao_market_data.sql`: tuning do Postgres/TimescaleDB.
  - `import_csv.py`: importador de CSV (ex.: `dados_historicos.csv`) para dentro do banco.

## Pasta `sql/`

- `features_labels.sql`: SQLs de features/labels para ML.

## Pasta `systemd/`

- Serviços/timers systemd para orquestrar a API e tarefas de saúde em ambientes Linux:
  - `mt5-api.service`, `mt5-compose.service`: serviços para iniciar a API/stack.
  - `mt5-healthcheck.service` e `mt5-healthcheck.timer`: healthchecks agendados.
  - `mt5-scheduler.service`: serviço para o scheduler.

## Pastas de dados e logs

- `data/` e `volumes/`:
  - `data/raw/`, `volumes/timescaledb/`: dados locais e volumes persistentes (o Postgres monta sua pasta de dados via volume `db_data`).
- `logs/` e `logrotate.d/`:
  - Configurações e diretórios para logs de execução, com regras de rotação (`logrotate.d/mt5`).

## Outros diretórios/arquivos

- `env/`, `env.template`: templates e helpers de variáveis de ambiente.
- `ssh/`: chaves/arquivo de SSH (se usado para deploys/backs privados).
- `init-scripts/`: scripts de inicialização suplementares.
- `monitor_dados.sh`, `fix_docker.sh`: utilidades para monitorar/coletar dados e ajustar docker local.
- `symbol`, `timeframe`: recursos auxiliares com listas de símbolos e granularidades.

---

## Fluxo dos serviços (visão geral)

1. `db` (TimescaleDB): provê armazenamento para `market_data`, features, fila de sinais, etc.
2. `api` (FastAPI): expõe endpoints REST:
   - `/ingest` recebe candles (single ou batch) com API Key.
   - `/signals/*` entrega sinais para consumidores (EA, serviços externos).
3. `ml-trainer` (jobs batch): prepara dataset (`prepare_dataset.py`) e treina modelo(s), salvando em `models/`.
4. `ml-scheduler` (processo contínuo): periodicamente lê features, executa modelo e injeta sinais nas tabelas.
5. `pgadmin`: UI do Postgres para inspeção/consulta.

## Convenções e Segurança

- Autenticação
  - API Key via header `X-API-Key` para endpoints sensíveis (ex.: `/ingest`, `/signals/*`).
- SQL
  - Uso de SQLAlchemy `text()` com parâmetros nomeados para evitar injection.
- Commits/Transações
  - Operações críticas usam `ENGINE.begin()` para garantir atomicidade.

## Dicas de Operação

- Subir stack completo:
  - `make up`
- Verificar status de containers:
  - `make ps`
- Logs de todos os serviços:
  - `make logs`
- Testar ingest (exemplo):
  - `curl -X POST http://localhost:18001/ingest -H "Content-Type: application/json" -H "X-API-Key: supersecretkey" -d '{"items":[{"ts":"2025-10-17T16:30:00Z","symbol":"EURUSD","timeframe":"M1","open":1.1,"high":1.1005,"low":1.0995,"close":1.1003,"volume":100}]}'`
- Verificar inserções recentes:
  - `docker compose exec db psql -U trader -d mt5_trading -c "SELECT COUNT(*) FILTER (WHERE ts>now()-INTERVAL '5 min') AS rows_5min FROM market_data;"`

---

Se quiser, posso adicionar diagramas com o fluxo de dados (ingest → DB → features → treino → modelo → sinais) e uma tabela com as principais tabelas/views do banco para referência rápida.
