# Observabilidade: Prometheus e Grafana

## Prometheus
- **URL:** http://localhost:9090
- **Configuração:** `prometheus.yml` na raiz do projeto.
- **Scrape:** Coleta métricas do serviço `api` (porta 8000 interna do container) e do próprio Prometheus.
- **Exemplo de métrica customizada:**
  - `ingest_candles_inserted_total` (exposta pelo FastAPI em `/prometheus`)
- **Como acessar:**
  1. Suba os containers: `docker compose up -d prometheus`
  2. Acesse o dashboard web: http://localhost:9090
  3. Busque por métricas como `ingest_candles_inserted_total`

## Grafana
- **URL:** http://localhost:3000
- **Login padrão:**
  - Usuário: `admin`
  - Senha: `admin`
- **Primeiro uso:**
  1. Suba o serviço: `docker compose up -d grafana`
  2. Acesse http://localhost:3000
  3. Adicione o Prometheus como fonte de dados (URL: `http://prometheus:9090`)
  4. Importe dashboards ou crie gráficos customizados usando as métricas do Prometheus.


## Monitoramento Dinâmico do Servidor e Containers

### Serviços Adicionais
- **node-exporter**: expõe métricas do host Linux (CPU, RAM, disco, rede) em http://localhost:9100
- **cAdvisor**: expõe métricas detalhadas de containers Docker em http://localhost:8080

Ambos já estão integrados ao docker-compose e configurados para serem monitorados pelo Prometheus.

### Dashboard Grafana Pronto
- Arquivo: `grafana_dashboard_mt5.json` (raiz do projeto)
- Importação:
  1. Acesse o Grafana (http://localhost:3000)
  2. Menu lateral → Dashboards → Import
  3. Faça upload do arquivo `grafana_dashboard_mt5.json`
  4. Selecione a fonte de dados Prometheus

### O que o dashboard mostra?
- Candles ingeridos (total e taxa)
- Uso de CPU e memória por container
- Tráfego de rede do host

Você pode customizar, clonar ou expandir os gráficos conforme sua necessidade.

## Dicas
- Para customizar o Prometheus, edite o arquivo `prometheus.yml`.
- Para persistir dashboards do Grafana, utilize o volume `grafana_data`.

---

# Observability: Prometheus and Grafana (EN)

## Prometheus
- **URL:** http://localhost:9090
- **Config:** `prometheus.yml` at project root.
- **Scrapes:** Collects metrics from `api` service (port 8000 inside container) and itself.
- **Custom metric example:**
  - `ingest_candles_inserted_total` (exposed by FastAPI at `/prometheus`)
- **How to access:**
  1. Start containers: `docker compose up -d prometheus`
  2. Open web UI: http://localhost:9090
  3. Search for metrics like `ingest_candles_inserted_total`

## Grafana
- **URL:** http://localhost:3000
- **Default login:**
  - User: `admin`
  - Password: `admin`
- **First use:**
  1. Start service: `docker compose up -d grafana`
  2. Open http://localhost:3000
  3. Add Prometheus as data source (URL: `http://prometheus:9090`)
  4. Import dashboards or create custom charts using Prometheus metrics.

## Dashboard Examples
- Create a panel with the `ingest_candles_inserted_total` metric to monitor real-time ingestions.
- Use filters by job, endpoint, etc.

## Tips
- To customize Prometheus, edit `prometheus.yml`.
- To persist Grafana dashboards, use the `grafana_data` volume.
