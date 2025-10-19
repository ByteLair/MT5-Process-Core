# MT5 Trading System - Documentação Técnica Completa

## Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Componentes](#componentes)
4. [Instalação e Setup](#instalação-e-setup)
5. [API Reference](#api-reference)
6. [Machine Learning](#machine-learning)
7. [Monitoramento e Observabilidade](#monitoramento-e-observabilidade)
8. [Backup e Disaster Recovery](#backup-e-disaster-recovery)
9. [Automação e Manutenção](#automação-e-manutenção)
10. [Segurança](#segurança)
11. [Troubleshooting](#troubleshooting)
12. [Contribuindo](#contribuindo)

---

## Visão Geral

### Propósito
Sistema completo de trading automatizado com MT5 (MetaTrader 5) que integra:
- Coleta e armazenamento de dados de mercado
- Machine Learning para geração de sinais
- API REST para integração
- Monitoramento e observabilidade completa
- Automação de operações e manutenção

### Stack Tecnológico
- **Backend**: Python (FastAPI), PostgreSQL (TimescaleDB), PgBouncer
- **ML**: Scikit-learn, LightGBM, PyTorch
- **Observabilidade**: Prometheus, Grafana, Loki, Promtail, Jaeger
- **Containerização**: Docker, Docker Compose
- **Automação**: Systemd, Bash, GitHub Actions
- **Backup**: SCP/SSH para servidor remoto

---

## Arquitetura do Sistema

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                         MT5 Trading System                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌─────────────┐  │
│  │   MT5 Data   │─────▶│     API      │◀─────│   Grafana   │  │
│  │  Collector   │      │  (FastAPI)   │      │  Dashboard  │  │
│  └──────────────┘      └──────────────┘      └─────────────┘  │
│         │                      │                      │         │
│         │                      │                      │         │
│         ▼                      ▼                      ▼         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              PostgreSQL + TimescaleDB                    │  │
│  │                    (via PgBouncer)                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│         │                                                       │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐      ┌──────────────┐      ┌─────────────┐  │
│  │  ML Worker   │─────▶│   Models     │─────▶│  Signals    │  │
│  │ (Training)   │      │   (ML/AI)    │      │ Generation  │  │
│  └──────────────┘      └──────────────┘      └─────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Observability Stack (Prometheus, Loki, Jaeger)   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │      Automation (Systemd Timers, GitHub Actions)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

1. **Ingestão**: Dados de mercado coletados do MT5 → API `/ingest` → PostgreSQL
2. **Processamento**: Features calculadas via SQL (02-features.sql)
3. **Treinamento**: ML Worker lê features → treina modelo → salva em `ml/models/`
4. **Predição**: API lê modelo → calcula sinais → retorna via `/signals`
5. **Monitoramento**: Todos os serviços enviam métricas → Prometheus/Loki → Grafana

---

## Componentes

### 1. Banco de Dados (PostgreSQL + TimescaleDB)

**Localização**: Container `mt5_db`
**Porta**: 5432 (via PgBouncer: 6432)

#### Tabelas Principais

- `market_data`: Dados OHLCV de mercado (hypertable TimescaleDB)
- `features_m1`: Features calculadas para ML
- `model_signals`: Sinais gerados pelo modelo
- `model_metrics`: Métricas de avaliação dos modelos

#### Scripts de Inicialização

- `db/init/01-init.sql`: Criação de tabelas base
- `db/init/02-features.sql`: Views e features
- `db/init/03-roles.sql`: Usuários e permissões

### 2. API (FastAPI)

**Localização**: `api/`
**Porta**: 8001
**Container**: `mt5_api`

#### Endpoints Principais

- `GET /health`: Status da API
- `GET /signals`: Sinais atuais para todos os símbolos
- `POST /signals/save`: Persiste sinais no banco
- `GET /signals/history`: Histórico de sinais
- `GET /signals/latest`: Últimos sinais salvos
- `GET /metrics`: Métricas do modelo atual
- `GET /prometheus`: Métricas para Prometheus

#### Módulos

- `api/app/main.py`: Aplicação principal
- `api/signals.py`: Geração de sinais
- `api/metrics.py`: Métricas de modelo
- `api/predict.py`: Predições ML
- `api/session.py`: Gerenciamento de sessões

### 3. Machine Learning

**Localização**: `ml/`
**Container**: `ml-scheduler`

#### Scripts de Treinamento

- `ml/worker/train.py`: Treinamento do modelo RandomForest
- `ml/train_model.py`: Pipeline completo de treinamento
- `ml/prepare_dataset.py`: Preparação de dados

#### Modelos

- `ml/models/rf_m1.pkl`: Modelo RandomForest para M1
- `ml/models/manifest.json`: Metadados e métricas

### 4. Observabilidade

#### Prometheus
**Porta**: 9090
**Config**: `prometheus/prometheus.yml`
**Métricas**:
- Métricas da API (FastAPI)
- Node Exporter (sistema)
- PgBouncer (conexões)
- Métricas customizadas

#### Grafana
**Porta**: 3000
**Dashboards**:
- `mt5-trading-main.json`: Dashboard principal
- `mt5-infra-logs.json`: Infraestrutura e logs
- `mt5-db-dashboard.json`: Banco de dados
- `mt5-ml-dashboard.json`: Machine Learning

#### Loki + Promtail
**Porta**: 3100
**Config**: `loki/loki-config.yml`, `loki/promtail-config.yml`
**Logs coletados**:
- Containers Docker
- API logs
- ML logs
- Health checks
- Sistema (syslog)

#### Jaeger
**Porta**: 16686
**Tracing**: Rastreamento distribuído de requisições

### 5. Automação (Systemd)

**Localização**: `systemd/`

#### Serviços e Timers

- `mt5-update.{service,timer}`: Atualização diária (04:00)
- `mt5-tests.{service,timer}`: Testes automatizados (04:00)
- `mt5-daily-report.{service,timer}`: Relatório unificado (04:00)
- `mt5-vuln-check.{service,timer}`: Verificação de vulnerabilidades (04:00)
- `mt5-remote-backup.{service,timer}`: Backup remoto (04:00)
- `github-runner-check.{service,timer}`: Monitor do GitHub Actions Runner (04:00)
- `github-runner-start.service`: Inicia runner no boot
- `mt5-maintenance.{service,timer}`: Manutenção programada

### 6. Scripts

**Localização**: `scripts/`

#### Operacionais
- `maintenance.sh`: Manutenção completa do sistema
- `health-check.sh`: Verificação de saúde com SQLite
- `backup.sh`: Backup local
- `restore.sh`: Restauração de backup
- `remote_backup.sh`: Backup para servidor remoto

#### Instalação
- `install_maintenance_systemd.sh`: Instala serviços de manutenção
- `install_update_systemd.sh`: Instala serviços de atualização
- `start_github_runner.sh`: Inicia GitHub Actions Runner

#### Monitoramento
- `check_github_runner.sh`: Verifica status do runner
- `check_vulnerabilities.sh`: Scan de vulnerabilidades
- `daily_report.sh`: Relatório diário unificado
- `git_commit_email_notify.sh`: Notificação de commits

---

## Instalação e Setup

### Pré-requisitos

- Linux (Ubuntu 20.04+ recomendado)
- Docker e Docker Compose
- Python 3.9+
- Git
- SSH (para backup remoto)
- Mailx/Postfix (para alertas por email)

### Instalação Rápida

```bash
# 1. Clone o repositório
git clone https://github.com/Lysk-dot/mt5-trading-db.git
cd mt5-trading-db

# 2. Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# 3. Inicie os containers
docker compose up -d

# 4. Verifique o status
docker compose ps
bash scripts/maintenance.sh status

# 5. Configure automação
bash scripts/install_maintenance_systemd.sh
bash scripts/install_update_systemd.sh

# 6. Configure GitHub Actions Runner (se necessário)
bash scripts/start_github_runner.sh
```

### Configuração de Email (Alertas)

```bash
# Instale mailx
sudo apt-get install mailutils

# Configure SMTP no sistema ou use relay
# Edite /etc/postfix/main.cf se necessário
```

### Configuração de Backup Remoto

```bash
# Configure autenticação SSH sem senha
ssh-keygen -t rsa -b 4096
ssh-copy-id felipe@100.113.13.126

# Teste o backup
bash scripts/remote_backup.sh

# Ative o timer
sudo systemctl enable --now mt5-remote-backup.timer
```

### Acesso aos Serviços

- **API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **PgAdmin**: http://localhost:5050

---

## API Reference

### Authentication
*Atualmente sem autenticação. Para produção, implemente OAuth2/JWT.*

### Endpoints

#### Health Check
```http
GET /health
```
**Response**:
```json
{
  "status": "ok"
}
```

#### Get Current Signals
```http
GET /signals?timeframe=M1
```
**Parameters**:
- `timeframe` (string): M1, M5, M15, M30, H1, H4, D1

**Response**:
```json
[
  {
    "symbol": "EURUSD",
    "timeframe": "M1",
    "ts": "2025-10-18T10:00:00",
    "prob_up": 0.65,
    "label": 1
  }
]
```

#### Save Signals
```http
POST /signals/save?timeframe=M1
```
**Response**:
```json
{
  "saved": 10,
  "timeframe": "M1"
}
```

#### Get Signal History
```http
GET /signals/history?symbol=EURUSD&timeframe=M1&limit=100
```
**Response**: Array de sinais históricos

#### Get Latest Saved Signals
```http
GET /signals/latest?timeframe=M1
```
**Response**: Último sinal salvo para cada símbolo

#### Get Model Metrics
```http
GET /metrics
```
**Response**:
```json
{
  "current": {
    "model_name": "rf_m1",
    "metrics": {
      "accuracy": 0.65,
      "precision": 0.68,
      "recall": 0.62
    }
  },
  "last_db": { ... }
}
```

---

## Machine Learning

### Pipeline de Treinamento

1. **Coleta de Dados**: Market data → PostgreSQL
2. **Feature Engineering**: SQL views calculam indicadores técnicos
3. **Preparação**: `prepare_dataset.py` extrai features
4. **Treinamento**: `train.py` treina RandomForest
5. **Avaliação**: Métricas salvas em `manifest.json` e banco
6. **Deploy**: Modelo salvo em `ml/models/rf_m1.pkl`

### Features Utilizadas

- `close`: Preço de fechamento
- `volume`: Volume
- `spread`: Spread
- `rsi`: Relative Strength Index
- `macd`, `macd_signal`, `macd_hist`: MACD indicators
- `atr`: Average True Range
- `ma60`: Moving Average 60
- `ret_1`: Retorno de 1 período

### Target

- `fwd_ret_5 > 0`: Retorno futuro de 5 períodos positivo (classificação binária)

### Modelo

- **Tipo**: RandomForestClassifier
- **Parâmetros**: n_estimators=200, random_state=42
- **Threshold**: Otimizado para maximizar F1-score

### Retreinamento

Execute manualmente:
```bash
docker compose exec ml python ml/worker/train.py
```

Ou via scheduler (se configurado):
```bash
docker compose exec ml python ml/scheduler.py
```

---

## Monitoramento e Observabilidade

### Dashboards Grafana

#### MT5 Trading Main
- Total de candles inseridos
- Status da API
- Registros no banco
- Taxa de ingestão
- Distribuição por símbolo
- Gráficos de preço

#### Infra & Logs
- Logs centralizados (Loki)
- Erros críticos
- Uso de CPU/Memória/Disco
- Containers ativos
- Fila do PgBouncer
- Tráfego de rede

#### Database
- Total de registros
- Símbolos ativos
- Distribuição de dados
- Performance de queries

#### ML/AI
- Logs do worker
- Jobs de treinamento
- Taxa de sucesso/falha

### Alertas

#### Configurados
- API Down (Prometheus `up{job="mt5-api"}==0`)
- Email: kuramopr@gmail.com

#### Adicionar Novos Alertas
Edite `grafana/provisioning/alerting/api-down-rule.yaml`

### Logs

#### Locais
- API: `logs/api/api.log`
- ML: `logs/ml/train.log`
- Health checks: `logs/health-checks/*.log`
- Sistema: `/var/log/syslog`

#### Centralização
Todos os logs são enviados para Loki via Promtail e visualizados no Grafana.

---

## Backup e Disaster Recovery

### Backup Local

```bash
bash scripts/backup.sh
```
Salva em `backups/backup_YYYY-MM-DD.tar.gz`

### Backup Remoto

```bash
bash scripts/remote_backup.sh
```
Envia para `100.113.13.126:/home/felipe/mt5-backup/YYYY-MM-DD/`

**Conteúdo**:
- Dump do banco de dados
- Modelos ML
- Configurações (Grafana, Prometheus, Loki)
- Scripts e código
- Logs

**Automação**: Timer systemd às 04:00 diariamente

### Restauração

```bash
bash scripts/restore.sh /path/to/backup.tar.gz
```

### Disaster Recovery

1. **Setup novo servidor**: Instale Docker, Git, dependências
2. **Clone repositório**: `git clone ...`
3. **Restaure backup**: `bash scripts/restore.sh`
4. **Inicie containers**: `docker compose up -d`
5. **Verifique saúde**: `bash scripts/health-check.sh`

---

## Automação e Manutenção

### Serviços Automáticos

Todos executam diariamente às 04:00:

1. **Atualização**: Atualiza código, imagens, dependências
2. **Testes**: Executa suite completa de testes
3. **Verificação de vulnerabilidades**: Scan de dependências
4. **Backup remoto**: Backup completo para servidor externo
5. **Relatório diário**: Email unificado com status

### Health Checks

```bash
bash scripts/health-check.sh
```

Verifica:
- Containers Docker
- Endpoints da API
- Banco de dados
- Espaço em disco
- GitHub Actions Runner

**Logs**: SQLite em `logs/health-checks/health_checks.db`

**Relatório**:
```bash
bash scripts/health-check.sh --report
```

### Manutenção

```bash
# Status geral
bash scripts/maintenance.sh status

# Manutenção completa
bash scripts/maintenance.sh full

# Limpeza
bash scripts/maintenance.sh cleanup

# Reiniciar serviços
bash scripts/maintenance.sh restart
```

---

## Segurança

### Práticas Implementadas

- Connection pooling (PgBouncer)
- Logs centralizados
- Health checks automatizados
- Backup redundante
- Scan de vulnerabilidades diário

### Recomendações para Produção

1. **Autenticação**: Implemente OAuth2/JWT na API
2. **TLS/SSL**: Configure HTTPS para todos os endpoints
3. **Secrets**: Use Docker secrets ou Vault
4. **Firewall**: Restrinja portas e IPs permitidos
5. **Roles**: Restrinja permissões de banco
6. **Updates**: Mantenha dependências atualizadas
7. **Auditoria**: Registre acessos e mudanças críticas

---

## Troubleshooting

### API não responde

```bash
# Verifique o container
docker logs mt5_api

# Reinicie
docker compose restart api

# Verifique health
curl http://localhost:8001/health
```

### Banco de dados lento

```bash
# Verifique métricas no Grafana
# Dashboard: MT5 Database

# Conexões do PgBouncer
docker logs mt5_pgbouncer

# Vacuum e análise
docker exec mt5_db psql -U trader -d mt5_trading -c "VACUUM ANALYZE;"
```

### Espaço em disco baixo

```bash
# Limpe logs antigos
bash scripts/maintenance.sh cleanup

# Limpe containers e imagens antigas
docker system prune -a
```

### Modelo ML não está gerando sinais

```bash
# Verifique se o modelo existe
ls -lh ml/models/

# Retreine o modelo
docker compose exec ml python ml/worker/train.py

# Verifique logs
docker logs ml-scheduler
```

### GitHub Actions Runner offline

```bash
# Verifique status
systemctl status actions.runner.Lysk-dot-mt5-trading-db.2v4g1.service

# Reinicie
bash scripts/start_github_runner.sh
```

### Alertas não chegam por email

```bash
# Teste envio de email
echo "Teste" | mailx -s "Teste" kuramopr@gmail.com

# Verifique logs do Postfix
sudo tail -f /var/log/mail.log

# Verifique configuração do Grafana
# grafana.ini [smtp]
```

---

## Contribuindo

### Estrutura de Commits

```
<tipo>: <descrição curta>

<descrição detalhada>

<footer>
```

**Tipos**: feat, fix, docs, style, refactor, test, chore

### Pull Requests

1. Fork o repositório
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

### Testes

```bash
# Execute todos os testes
pytest

# Testes específicos
pytest api/tests/
pytest ml/tests/
pytest scripts/tests/
```

---

## Licença

*Adicione a licença do projeto aqui*

---

## Contato

- **Maintainer**: Felipe (kuramopr@gmail.com)
- **Repository**: https://github.com/Lysk-dot/mt5-trading-db

---

## Changelog

### 2025-10-18
- Documentação completa criada
- Sistema de backup remoto implementado
- Testes automatizados expandidos
- Alertas por email configurados
- Dashboards Grafana aprimorados
