# MT5 Trading System - Diagramas de Arquitetura

## Arquitetura Geral do Sistema

```mermaid
graph TB
    subgraph "External"
        MT5[MT5 Terminal/DataCollector]
        User[User/Trader]
        RemoteBackup[Backup Server<br/>100.113.13.126]
    end

    subgraph "API Layer"
        API[FastAPI<br/>Port 8001]
        APIMetrics[/prometheus<br/>metrics]
    end

    subgraph "Data Layer"
        PgBouncer[PgBouncer<br/>Connection Pool<br/>Port 6432]
        DB[(PostgreSQL<br/>TimescaleDB<br/>Port 5432)]
    end

    subgraph "ML Layer"
        MLWorker[ML Worker<br/>Training]
        MLScheduler[ML Scheduler]
        MLModels[Models Storage<br/>ml/models/]
    end

    subgraph "Observability Stack"
        Prometheus[Prometheus<br/>Port 9090]
        Grafana[Grafana<br/>Port 3000]
        Loki[Loki<br/>Port 3100]
        Promtail[Promtail<br/>Log Collector]
        Jaeger[Jaeger<br/>Port 16686]
    end

    subgraph "Automation"
        Systemd[Systemd Timers]
        GHRunner[GitHub Actions<br/>Runner]
        Scripts[Maintenance Scripts]
    end

    MT5 -->|POST /ingest| API
    User -->|HTTP Requests| API
    API -->|Queries| PgBouncer
    PgBouncer -->|Connection Pool| DB

    MLScheduler -->|Triggers| MLWorker
    MLWorker -->|Reads Features| DB
    MLWorker -->|Saves Models| MLModels
    API -->|Loads Models| MLModels
    API -->|Generates Signals| DB

    API -->|Metrics| Prometheus
    DB -->|Metrics| Prometheus
    Prometheus -->|Data Source| Grafana

    API -->|Logs| Promtail
    MLWorker -->|Logs| Promtail
    Promtail -->|Push| Loki
    Loki -->|Data Source| Grafana

    API -->|Traces| Jaeger
    Jaeger -->|Data Source| Grafana

    Systemd -->|Runs| Scripts
    Scripts -->|Maintenance| API
    Scripts -->|Maintenance| DB
    Scripts -->|Backup| RemoteBackup
    GHRunner -->|CI/CD| API

    style API fill:#4CAF50
    style DB fill:#2196F3
    style Prometheus fill:#E96228
    style Grafana fill:#F46800
    style MLWorker fill:#9C27B0
```

## Fluxo de Dados - Ingestão

```mermaid
sequenceDiagram
    participant MT5 as MT5 DataCollector
    participant API as FastAPI
    participant PgBouncer as PgBouncer
    participant DB as PostgreSQL
    participant Prom as Prometheus

    MT5->>API: POST /ingest (OHLCV data)
    API->>API: Validate payload
    API->>PgBouncer: Get connection
    PgBouncer->>DB: Connect
    DB-->>PgBouncer: Connection
    PgBouncer-->>API: Connection
    API->>DB: INSERT INTO market_data
    DB-->>API: Success
    API->>Prom: Increment ingest_candles_total
    API-->>MT5: 200 OK
```

## Fluxo de Dados - Geração de Sinais

```mermaid
sequenceDiagram
    participant User as User/System
    participant API as FastAPI
    participant DB as PostgreSQL
    participant ML as ML Model
    participant Cache as Models Cache

    User->>API: GET /signals?timeframe=M1
    API->>Cache: Load model (rf_m1.pkl)
    alt Model not in cache
        Cache->>ML: Load from disk
        ML-->>Cache: Model object
    end
    Cache-->>API: Model ready

    API->>DB: SELECT features FROM features_m1
    DB-->>API: Feature data

    API->>ML: model.predict_proba(features)
    ML-->>API: Probabilities

    API->>API: Apply threshold
    API->>API: Generate signals
    API-->>User: JSON with signals
```

## Fluxo de Dados - Treinamento ML

```mermaid
sequenceDiagram
    participant Scheduler as ML Scheduler
    participant Worker as ML Worker
    participant DB as PostgreSQL
    participant FS as File System
    participant Metrics as Metrics DB

    Scheduler->>Worker: Trigger training
    Worker->>DB: SELECT * FROM trainset_m1
    DB-->>Worker: Training data

    Worker->>Worker: Prepare features (X, y)
    Worker->>Worker: Train RandomForest
    Worker->>Worker: Evaluate model

    Worker->>FS: Save model (rf_m1.pkl)
    Worker->>FS: Save manifest.json
    Worker->>Metrics: INSERT model_metrics
    Worker->>Scheduler: Training complete
```

## Fluxo de Monitoramento

```mermaid
graph LR
    subgraph "Sources"
        API[API Metrics]
        DB[DB Metrics]
        Node[Node Exporter]
        Logs[Application Logs]
        Traces[Traces]
    end

    subgraph "Collection"
        Prom[Prometheus<br/>Scrape]
        Promtail[Promtail<br/>Push]
        Jaeger[Jaeger<br/>Collect]
    end

    subgraph "Storage"
        PromDB[(Prometheus DB)]
        LokiDB[(Loki DB)]
        JaegerDB[(Jaeger DB)]
    end

    subgraph "Visualization"
        Grafana[Grafana<br/>Dashboards]
    end

    subgraph "Alerting"
        Alerts[Alert Rules]
        Email[Email<br/>kuramopr@gmail.com]
    end

    API -->|metrics| Prom
    DB -->|metrics| Prom
    Node -->|metrics| Prom
    Prom -->|store| PromDB

    Logs -->|logs| Promtail
    Promtail -->|push| LokiDB

    Traces -->|traces| Jaeger
    Jaeger -->|store| JaegerDB

    PromDB -->|query| Grafana
    LokiDB -->|query| Grafana
    JaegerDB -->|query| Grafana

    Grafana -->|evaluate| Alerts
    Alerts -->|notify| Email
```

## Automação e Manutenção

```mermaid
graph TB
    subgraph "Daily Schedule (04:00)"
        Timer[Systemd Timers]
    end

    subgraph "Services"
        Update[mt5-update<br/>Update system]
        Tests[mt5-tests<br/>Run tests]
        Vuln[mt5-vuln-check<br/>Security scan]
        Backup[mt5-remote-backup<br/>Backup to remote]
        Report[mt5-daily-report<br/>Email report]
        RunnerCheck[github-runner-check<br/>Monitor runner]
    end

    subgraph "Actions"
        UpdateCode[Pull git<br/>Update images<br/>Update deps]
        RunTests[Pytest API<br/>Pytest ML<br/>Pytest Scripts]
        ScanVuln[Safety check<br/>npm audit]
        BackupDB[pg_dump<br/>Tar files<br/>SCP remote]
        GenReport[Status services<br/>Last commits<br/>Test results]
        CheckRunner[systemctl status<br/>Alert if offline]
    end

    subgraph "Notifications"
        Email[Email to<br/>kuramopr@gmail.com]
    end

    Timer -->|04:00| Update
    Timer -->|04:00| Tests
    Timer -->|04:00| Vuln
    Timer -->|04:00| Backup
    Timer -->|04:00| Report
    Timer -->|04:00| RunnerCheck

    Update --> UpdateCode
    Tests --> RunTests
    Vuln --> ScanVuln
    Backup --> BackupDB
    Report --> GenReport
    RunnerCheck --> CheckRunner

    UpdateCode --> Email
    RunTests --> Email
    ScanVuln --> Email
    BackupDB --> Email
    GenReport --> Email
    CheckRunner --> Email
```

## Backup e Disaster Recovery

```mermaid
graph LR
    subgraph "Production Server"
        DB[(PostgreSQL)]
        Files[Files<br/>models, configs, logs]
        Services[Services<br/>Grafana, Prometheus, Loki]
    end

    subgraph "Backup Process"
        Script[remote_backup.sh]
        Dump[pg_dump]
        Tar[tar czf]
        SCP[scp to remote]
    end

    subgraph "Backup Server (100.113.13.126)"
        Remote[(Backup Storage<br/>/home/felipe/mt5-backup/YYYY-MM-DD/)]
    end

    subgraph "Restore Process"
        RestoreScript[restore.sh]
        ExtractTar[tar xzf]
        RestoreDB[psql restore]
    end

    DB -->|dump| Dump
    Files -->|compress| Tar
    Services -->|compress| Tar

    Dump --> Script
    Tar --> Script
    Script --> SCP
    SCP --> Remote

    Remote -->|on disaster| RestoreScript
    RestoreScript --> ExtractTar
    RestoreScript --> RestoreDB
    ExtractTar -->|files| Files
    RestoreDB -->|data| DB
```

## Health Check System

```mermaid
graph TB
    subgraph "Health Check Script"
        HealthScript[health-check.sh]
    end

    subgraph "Checks"
        Containers[Docker Containers<br/>mt5_db, mt5_api, etc]
        APIs[API Endpoints<br/>/health, /docs, etc]
        Database[Database<br/>Connection, Size, Records]
        Disk[Disk Space<br/>Usage threshold]
        Runner[GitHub Runner<br/>systemd status]
    end

    subgraph "Storage"
        SQLite[(health_checks.db<br/>SQLite)]
    end

    subgraph "Analysis"
        Stats[Calculate stats<br/>Avg, Min, Max]
        Alerts[Alert Rules<br/>Consecutive failures]
        Report[Daily Report<br/>Summary]
    end

    subgraph "Actions"
        Email[Email Alert<br/>kuramopr@gmail.com]
        Logs[Log Files]
    end

    HealthScript --> Containers
    HealthScript --> APIs
    HealthScript --> Database
    HealthScript --> Disk
    HealthScript --> Runner

    Containers --> SQLite
    APIs --> SQLite
    Database --> SQLite
    Disk --> SQLite
    Runner --> SQLite

    SQLite --> Stats
    SQLite --> Alerts
    SQLite --> Report

    Alerts --> Email
    Report --> Email
    Stats --> Logs
```

## CI/CD Pipeline (GitHub Actions)

```mermaid
graph LR
    subgraph "Trigger"
        Push[git push]
        PR[Pull Request]
    end

    subgraph "GitHub Actions"
        Checkout[Checkout code]
        Setup[Setup Python/Docker]
        Lint[Lint code]
        Test[Run tests]
        Build[Build images]
        Deploy[Deploy to server]
    end

    subgraph "Runner"
        SelfHosted[Self-hosted Runner<br/>actions.runner.Lysk-dot]
    end

    subgraph "Notifications"
        Email[Email on commit<br/>kuramopr@gmail.com]
        Status[Status checks]
    end

    Push --> Checkout
    PR --> Checkout

    Checkout --> Setup
    Setup --> Lint
    Lint --> Test
    Test --> Build
    Build --> Deploy

    Deploy --> SelfHosted
    SelfHosted --> Status

    Push --> Email
    Test --> Status
```

## Database Schema (Simplified)

```mermaid
erDiagram
    MARKET_DATA ||--o{ FEATURES_M1 : generates
    FEATURES_M1 ||--o{ MODEL_SIGNALS : predicts
    MODEL_METRICS ||--o{ MODELS : tracks

    MARKET_DATA {
        timestamp ts PK
        string symbol
        string timeframe
        float open
        float high
        float low
        float close
        int volume
        float spread
    }

    FEATURES_M1 {
        timestamp ts PK
        string symbol
        string timeframe
        float close
        float volume
        float spread
        float rsi
        float macd
        float macd_signal
        float macd_hist
        float atr
        float ma60
        float ret_1
        float fwd_ret_5
    }

    MODEL_SIGNALS {
        timestamp ts PK
        string symbol
        string timeframe
        string model_name
        float threshold
        float prob_up
        int label
        timestamp created_at
    }

    MODEL_METRICS {
        int id PK
        timestamp created_at
        string model_name
        jsonb metrics
    }
```
