# 🏥 Health Check System Documentation

Sistema completo de monitoramento de saúde para containers, API, database e pipelines.

## 📋 Visão Geral

- **Health Check Script:** Bash script que monitora todos os componentes
- **SQLite Database:** Armazena histórico de checks e alertas
- **Web Dashboard:** Interface web simples em Flask (porta 5001)
- **Grafana Dashboard:** Integração com Grafana para visualização avançada
- **Automated Monitoring:** GitHub Actions executando a cada 5 minutos
- **Daily Reports:** Relatórios diários automáticos às 5:00 AM

## 🚀 Quick Start

### Executar Health Check Manual

```bash
cd /home/felipe/MT5-Process-Core-full
./scripts/health-check.sh
```

### Gerar Relatório Diário

```bash
./scripts/health-check.sh --report
```

### Iniciar Dashboard Web

```bash
# Instalar dependências
pip install flask

# Iniciar dashboard
python3 scripts/health-dashboard.py

# Acessar em: http://localhost:5001
```

## 📊 Componentes Monitorados

### 1. Docker Containers

- ✅ mt5_db (PostgreSQL/TimescaleDB)
- ✅ mt5_api (FastAPI)
- ✅ mt5_prometheus
- ✅ mt5_grafana
- ✅ mt5_pgadmin

**Métricas coletadas:**

- Status (healthy/unhealthy/down)
- CPU usage (%)
- Memory usage (%)
- Response time (ms)

### 2. API Endpoints

- ✅ API Health (<http://localhost:8001/health>)
- ✅ API Docs (<http://localhost:8001/docs>)
- ✅ Prometheus (<http://localhost:9090/-/healthy>)
- ✅ Grafana (<http://localhost:3000/api/health>)

**Métricas coletadas:**

- HTTP status code
- Response time (ms)

### 3. Database

- ✅ Connection test
- ✅ Database size
- ✅ Record count

### 4. System Resources

- ✅ Disk space usage
- ✅ Alerts on >80% usage

### 5. CI/CD

- ✅ GitHub Actions Runner status

## 🗄️ Database Schema

### Table: health_checks

```sql
CREATE TABLE health_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    check_type TEXT NOT NULL,          -- container, api, database, system, cicd
    component_name TEXT NOT NULL,      -- mt5_db, API Health, etc
    status TEXT NOT NULL,              -- healthy, unhealthy, down, warning, critical
    details TEXT,                      -- Additional information
    response_time_ms INTEGER,          -- Response time in milliseconds
    cpu_usage REAL,                    -- CPU percentage
    memory_usage REAL,                 -- Memory percentage
    disk_usage REAL                    -- Disk percentage
);
```

### Table: alerts

```sql
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    component_name TEXT NOT NULL,
    alert_type TEXT NOT NULL,          -- unhealthy, down, disk_full, etc
    message TEXT,
    resolved BOOLEAN DEFAULT 0,
    resolved_at DATETIME
);
```

## 📈 Dashboard Web (Flask)

### Features

- ✅ Real-time monitoring
- ✅ Auto-refresh every 30 seconds
- ✅ Statistics cards (24h)
- ✅ Recent checks table
- ✅ Active alerts display
- ✅ Responsive design

### API Endpoints

**GET /** - Main dashboard HTML

**GET /api/stats** - Get 24h statistics

```json
{
  "total_checks": 1440,
  "healthy_checks": 1420,
  "unhealthy_checks": 20,
  "active_alerts": 2
}
```

**GET /api/recent-checks?limit=50** - Get recent checks

```json
[
  {
    "id": 1234,
    "timestamp": "2025-10-18 10:30:00",
    "check_type": "container",
    "component_name": "mt5_api",
    "status": "healthy",
    "details": "running",
    "response_time_ms": 45,
    "cpu_usage": 12.5,
    "memory_usage": 15.3
  }
]
```

**GET /api/alerts** - Get active alerts

```json
[
  {
    "id": 5,
    "timestamp": "2025-10-18 10:25:00",
    "component_name": "mt5_db",
    "alert_type": "unhealthy",
    "message": "Component mt5_db has failed 3 times in the last 5 minutes",
    "resolved": 0
  }
]
```

**GET /api/component/{name}?hours=24** - Get component history

## 📊 Grafana Integration

### Dashboard Features

- 📈 Health status pie chart (24h)
- 📊 Total checks counter
- ✅ Healthy checks counter
- 🚨 Active alerts counter
- 📉 Response time trend graph
- 📋 Recent checks table

### Setup

1. Dashboard já está em: `grafana/dashboards/health-check-dashboard.json`

2. Será importado automaticamente quando subir o Grafana

3. Acesse: <http://localhost:3000/d/health-check-dash>

## ⏰ Automated Monitoring

### GitHub Actions Workflow

**Arquivo:** `.github/workflows/health-check.yml`

**Schedule:**

- Health check: A cada 5 minutos
- Daily report: 5:00 AM UTC-3 (8:00 AM UTC)

**Actions:**

1. Executa health check
2. Verifica alertas críticos
3. Gera warning no GitHub Actions se houver alertas
4. Gera relatório diário automático

### View Workflow Runs

<https://github.com/Lysk-dot/mt5-trading-db/actions/workflows/health-check.yml>

## 🚨 Alert System

### Alert Triggers

Alertas são criados quando:

- Componente falha **3 vezes consecutivas** em 5 minutos
- Disco atinge >90% de uso
- Database connection falha

### Alert Types

- `unhealthy` - Component unhealthy
- `down` - Component down/not running
- `disk_full` - Disk space critical
- `db_connection_failed` - Database unreachable
- `api_down` - API endpoint não responde
- `runner_down` - GitHub runner offline

### Resolving Alerts

Alerts são resolvidos automaticamente quando o componente volta ao normal após 3 checks consecutivos.

Manual resolution:

```sql
UPDATE alerts
SET resolved=1, resolved_at=datetime('now')
WHERE component_name='mt5_db';
```

## 📁 File Structure

```
/home/felipe/MT5-Process-Core-full/
├── scripts/
│   ├── health-check.sh           # Main health check script
│   └── health-dashboard.py       # Flask web dashboard
├── logs/
│   └── health-checks/
│       ├── health_checks.db      # SQLite database
│       └── daily_report_*.txt    # Daily reports
├── grafana/
│   └── dashboards/
│       └── health-check-dashboard.json
└── .github/
    └── workflows/
        └── health-check.yml      # Automated monitoring
```

## 🔧 Configuration

### Change Check Frequency

Edit `.github/workflows/health-check.yml`:

```yaml
schedule:
  - cron: '*/5 * * * *'  # Every 5 minutes
  # - cron: '*/10 * * * *'  # Every 10 minutes
  # - cron: '0 * * * *'     # Every hour
```

### Change Alert Threshold

Edit `scripts/health-check.sh`:

```bash
ALERT_THRESHOLD=3  # Number of consecutive failures
```

### Add New Component to Monitor

Edit `scripts/health-check.sh`:

```bash
check_containers() {
    local containers=("mt5_db" "mt5_api" "mt5_new_service")  # Add here
    # ...
}
```

## 📊 Query Examples

### Last 10 failed checks

```sql
SELECT * FROM health_checks
WHERE status IN ('unhealthy', 'down', 'critical')
ORDER BY timestamp DESC
LIMIT 10;
```

### Component uptime (last 24h)

```sql
SELECT
    component_name,
    COUNT(*) as total_checks,
    SUM(CASE WHEN status='healthy' THEN 1 ELSE 0 END) as healthy,
    ROUND(100.0 * SUM(CASE WHEN status='healthy' THEN 1 ELSE 0 END) / COUNT(*), 2) as uptime_percent
FROM health_checks
WHERE timestamp > datetime('now', '-24 hours')
GROUP BY component_name;
```

### Average response time per component

```sql
SELECT
    component_name,
    ROUND(AVG(response_time_ms), 0) as avg_response_ms,
    MIN(response_time_ms) as min_response_ms,
    MAX(response_time_ms) as max_response_ms
FROM health_checks
WHERE timestamp > datetime('now', '-24 hours')
  AND response_time_ms > 0
GROUP BY component_name;
```

### Active alerts

```sql
SELECT * FROM alerts
WHERE resolved=0
ORDER BY timestamp DESC;
```

## 🧪 Testing

### Test Health Check

```bash
./scripts/health-check.sh
```

### Test Dashboard

```bash
python3 scripts/health-dashboard.py &
curl http://localhost:5001/api/stats
```

### Test Database

```bash
sqlite3 logs/health-checks/health_checks.db "SELECT COUNT(*) FROM health_checks;"
```

### Trigger Manual Workflow

1. Go to: <https://github.com/Lysk-dot/mt5-trading-db/actions>
2. Select "Health Check Monitoring"
3. Click "Run workflow"

## 📈 Monitoring Best Practices

1. **Review daily reports** - Check `logs/health-checks/daily_report_*.txt` cada manhã

2. **Monitor active alerts** - Dashboard web ou Grafana

3. **Track trends** - Use Grafana para identificar padrões

4. **Set up notifications** - Configure Grafana alerts para notificações críticas

5. **Regular maintenance** - Limpe logs antigos periodicamente:

   ```bash
   # Keep last 30 days
   sqlite3 logs/health-checks/health_checks.db "DELETE FROM health_checks WHERE timestamp < datetime('now', '-30 days');"
   ```

## 🔍 Troubleshooting

### Dashboard não inicia

```bash
# Instalar Flask
pip install flask

# Verificar porta
lsof -i :5001
```

### Database locked

```bash
# Verificar processos usando o DB
fuser logs/health-checks/health_checks.db
```

### Health check falha

```bash
# Verificar permissões
chmod +x scripts/health-check.sh

# Verificar sqlite3
which sqlite3
```

### Grafana não mostra dados

1. Verificar se dashboard Flask está rodando (porta 5001)
2. Verificar datasource no Grafana
3. Verificar se há dados no database

## 📚 References

- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Grafana Dashboards](https://grafana.com/docs/grafana/latest/dashboards/)
- [GitHub Actions Cron](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)

---

**Última atualização:** Outubro 2025
**Status:** ✅ Ativo e funcionando
**Monitoramento:** Automático a cada 5 minutos
