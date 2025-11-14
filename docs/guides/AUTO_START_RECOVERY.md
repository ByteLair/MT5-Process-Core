# 🚀 Sistema de Auto-Start e Disaster Recovery

## Visão Geral

Sistema completo de **alta disponibilidade** que garante:
- ✅ **Zero perda de dados** em caso de reboot do servidor
- ✅ **Restart automático** de todos os containers
- ✅ **Backup diário** do banco de dados PostgreSQL
- ✅ **Healthcheck** a cada 15 minutos com auto-recovery
- ✅ **Recovery manual** para restaurar backups

---

## 🔧 Componentes Instalados

### 1. Systemd Service (`mt5-trading.service`)

**Localização**: `/etc/systemd/system/mt5-trading.service`

**Função**: Garante que o Docker Compose suba automaticamente no boot do servidor.

**Características**:
- Aguarda o Docker daemon estar pronto
- Executa `docker-compose up -d` automaticamente
- Reinicia se falhar
- Timeout de 5 minutos para start

**Comandos**:
```bash
# Ver status
sudo systemctl status mt5-trading

# Iniciar manualmente
sudo systemctl start mt5-trading

# Parar todos os containers
sudo systemctl stop mt5-trading

# Reiniciar todos os containers
sudo systemctl restart mt5-trading

# Ver logs
journalctl -u mt5-trading -f
```

---

### 2. Restart Policies (Docker Compose)

**Configuração**: Todos os 15 containers têm `restart: unless-stopped`

**Comportamento**:
- ✅ Reinicia automaticamente se crashar
- ✅ Reinicia automaticamente após reboot do servidor
- ❌ Não reinicia se você parar manualmente (`docker stop`)

**Containers protegidos**:
- `mt5_db` (PostgreSQL + TimescaleDB)
- `mt5_api` (FastAPI)
- `mt5_pgbouncer` (Connection pooler)
- `mt5_forex_updater` (Atualizador automático)
- `mt5_prometheus`, `mt5_grafana`, `mt5_loki`, `mt5_jaeger`
- `node-exporter`, etc.

---

### 3. Backup Automático Diário

**Script**: `/usr/local/bin/mt5-backup.sh`

**Horário**: Todo dia às **02:00**

**Retenção**: 7 dias (backups mais antigos são deletados)

**Localização dos backups**: `/var/backups/mt5/`

**O que é backupado**:
1. **Banco de dados PostgreSQL** (`mt5_db_YYYYMMDD_HHMMSS.sql.gz`)
2. **Volumes Docker** (`volumes_YYYYMMDD_HHMMSS.tar.gz`)

**Executar backup manual**:
```bash
sudo /usr/local/bin/mt5-backup.sh
```

**Ver logs de backup**:
```bash
tail -f /var/log/mt5-backup.log
```

**Tamanho estimado**:
- Banco com 1.8M candles: ~200-300 MB comprimido
- Volumes: ~50-100 MB

---

### 4. Healthcheck Automático

**Script**: `/usr/local/bin/mt5-healthcheck.sh`

**Frequência**: A cada **15 minutos**

**Containers monitorados**:
- `mt5_db`
- `mt5_api`
- `mt5_pgbouncer`
- `mt5_forex_updater`

**Ação em caso de problema**:
1. Detecta containers parados ou unhealthy
2. Loga o problema em `/var/log/mt5-healthcheck.log`
3. Executa `docker-compose restart` automaticamente
4. Aguarda 30 segundos
5. Confirma recuperação

**Ver logs de healthcheck**:
```bash
tail -f /var/log/mt5-healthcheck.log
```

**Executar healthcheck manual**:
```bash
sudo /usr/local/bin/mt5-healthcheck.sh
```

---

### 5. Recovery Manual

**Script**: `/usr/local/bin/mt5-recover.sh`

**Uso**: Restaurar banco de dados a partir de um backup

**Passos**:
```bash
# 1. Executar script
sudo /usr/local/bin/mt5-recover.sh

# 2. Listar backups disponíveis
📋 Backups disponíveis:
   /var/backups/mt5/mt5_db_20250114_020000.sql.gz (245M)
   /var/backups/mt5/mt5_db_20250113_020000.sql.gz (243M)
   ...

# 3. Digite o nome do arquivo (ex: mt5_db_20250114_020000.sql.gz)

# 4. Confirme com "yes"

# 5. Aguarde a restauração
```

**ATENÇÃO**: ⚠️ Isso **sobrescreve** o banco atual!

---

## 🧪 Testando o Sistema

### Teste 1: Verificar Auto-Start

```bash
# 1. Verificar se systemd service está habilitado
systemctl is-enabled mt5-trading
# Output esperado: enabled

# 2. Ver status
sudo systemctl status mt5-trading

# 3. Verificar restart policies
cd /home/lair/MT5-Process-Core
grep -A 1 "restart:" docker-compose.yml | grep unless-stopped | wc -l
# Output esperado: 15 (todos os containers)
```

### Teste 2: Simular Reboot

```bash
# 1. Anotar uptime dos containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# 2. Reiniciar servidor
sudo reboot

# 3. Após reboot, aguardar 2-3 minutos

# 4. Verificar se containers subiram
docker ps | grep mt5 | wc -l
# Output esperado: 12

# 5. Verificar dados intactos
docker exec mt5_db psql -U trader -d mt5_trading -c "SELECT COUNT(*) FROM market_data;"
# Output esperado: 1877965 (ou mais se houver updates)
```

### Teste 3: Simular Crash de Container

```bash
# 1. Parar container crítico
docker stop mt5_api

# 2. Aguardar alguns segundos
sleep 10

# 3. Verificar se reiniciou automaticamente
docker ps | grep mt5_api
# Output esperado: container rodando
```

### Teste 4: Backup e Recovery

```bash
# 1. Fazer backup manual
sudo /usr/local/bin/mt5-backup.sh

# 2. Verificar backup criado
ls -lh /var/backups/mt5/

# 3. (OPCIONAL - CUIDADO!) Testar recovery
sudo /usr/local/bin/mt5-recover.sh
```

---

## 📊 Monitoramento

### Verificar Status Geral

```bash
# Status do systemd service
sudo systemctl status mt5-trading

# Containers rodando
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}"

# Último backup
ls -lth /var/backups/mt5/ | head -5

# Logs de healthcheck
tail -20 /var/log/mt5-healthcheck.log

# Logs de backup
tail -20 /var/log/mt5-backup.log
```

### Verificar Integridade dos Dados

```bash
# Total de candles
docker exec mt5_db psql -U trader -d mt5_trading -c \
"SELECT COUNT(*) AS total_candles FROM market_data;"

# Último candle
docker exec mt5_db psql -U trader -d mt5_trading -c \
"SELECT symbol, timeframe, ts, close FROM market_data ORDER BY ts DESC LIMIT 1;"

# Coverage de indicadores
docker exec mt5_db psql -U trader -d mt5_trading -c \
"SELECT 
    COUNT(*) FILTER (WHERE rsi IS NOT NULL) * 100.0 / COUNT(*) AS rsi_coverage,
    COUNT(*) FILTER (WHERE macd IS NOT NULL) * 100.0 / COUNT(*) AS macd_coverage
FROM market_data WHERE timeframe = 'M1';"
```

---

## 🚨 Troubleshooting

### Problema: Containers não sobem após reboot

**Sintomas**:
```bash
docker ps | grep mt5
# Output: Nenhum container
```

**Solução**:
```bash
# 1. Verificar status do service
sudo systemctl status mt5-trading

# 2. Ver logs
journalctl -u mt5-trading -n 50

# 3. Tentar start manual
sudo systemctl start mt5-trading

# 4. Verificar erros no Docker Compose
cd /home/lair/MT5-Process-Core
docker-compose up -d
```

---

### Problema: Backup não está sendo executado

**Sintomas**:
```bash
ls /var/backups/mt5/
# Output: Nenhum backup recente
```

**Solução**:
```bash
# 1. Verificar crontab
sudo crontab -l

# 2. Executar backup manual para ver erros
sudo /usr/local/bin/mt5-backup.sh

# 3. Verificar logs
tail -50 /var/log/mt5-backup.log

# 4. Verificar se cron está rodando
sudo systemctl status cron

# 5. Re-adicionar ao cron se necessário
cat << 'CRON' | sudo crontab -
# MT5 Trading Platform - Backup e Healthcheck
0 2 * * * /usr/local/bin/mt5-backup.sh >> /var/log/mt5-backup.log 2>&1
*/15 * * * * /usr/local/bin/mt5-healthcheck.sh
CRON
```

---

### Problema: Healthcheck não está detectando problemas

**Sintomas**:
Container crash não é detectado automaticamente.

**Solução**:
```bash
# 1. Testar healthcheck manual
sudo /usr/local/bin/mt5-healthcheck.sh

# 2. Ver logs
tail -50 /var/log/mt5-healthcheck.log

# 3. Verificar cron
sudo crontab -l | grep healthcheck
```

---

### Problema: Disco cheio (backups ocupando muito espaço)

**Solução**:
```bash
# 1. Ver espaço usado por backups
du -sh /var/backups/mt5/

# 2. Listar backups
ls -lh /var/backups/mt5/

# 3. Deletar backups antigos manualmente
sudo rm /var/backups/mt5/mt5_db_20240101_*.sql.gz

# 4. Ou ajustar retenção no script (default: 7 dias)
sudo nano /usr/local/bin/mt5-backup.sh
# Alterar: RETENTION_DAYS=7 para RETENTION_DAYS=3
```

---

## 📁 Arquivos Importantes

| Arquivo | Função |
|---------|--------|
| `/etc/systemd/system/mt5-trading.service` | Systemd service para auto-start |
| `/usr/local/bin/mt5-backup.sh` | Script de backup diário |
| `/usr/local/bin/mt5-healthcheck.sh` | Script de healthcheck automático |
| `/usr/local/bin/mt5-recover.sh` | Script de recovery manual |
| `/var/backups/mt5/` | Diretório de backups |
| `/var/log/mt5-autostart.log` | Log do setup inicial |
| `/var/log/mt5-backup.log` | Logs de backup |
| `/var/log/mt5-healthcheck.log` | Logs de healthcheck |

---

## 🎯 Resumo da Proteção

| Cenário | Proteção | Como Funciona |
|---------|----------|---------------|
| **Reboot do servidor** | ✅ Automático | Systemd inicia Docker Compose |
| **Container crash** | ✅ Automático | Restart policy + healthcheck |
| **Perda de dados** | ✅ Backup diário | Backup às 02:00, retenção 7 dias |
| **Corrupção de DB** | ✅ Recovery manual | Script `/usr/local/bin/mt5-recover.sh` |
| **Falha silenciosa** | ✅ Healthcheck | Verifica a cada 15 minutos |

---

## 📞 Suporte

**Logs principais**:
```bash
# Auto-start
journalctl -u mt5-trading -f

# Backup
tail -f /var/log/mt5-backup.log

# Healthcheck
tail -f /var/log/mt5-healthcheck.log

# Docker Compose
cd /home/lair/MT5-Process-Core && docker-compose logs -f
```

**Comandos úteis**:
```bash
# Status geral
sudo systemctl status mt5-trading
docker ps

# Restart completo
sudo systemctl restart mt5-trading

# Ver backups
ls -lh /var/backups/mt5/

# Verificar dados
docker exec mt5_db psql -U trader -d mt5_trading -c "SELECT COUNT(*) FROM market_data;"
```

---

## ✅ Checklist Pós-Instalação

- [ ] Systemd service habilitado: `systemctl is-enabled mt5-trading`
- [ ] Todos os containers com restart policy: `grep restart docker-compose.yml`
- [ ] Cron configurado: `sudo crontab -l`
- [ ] Backup manual funciona: `sudo /usr/local/bin/mt5-backup.sh`
- [ ] Healthcheck manual funciona: `sudo /usr/local/bin/mt5-healthcheck.sh`
- [ ] Teste de reboot completo: `sudo reboot && docker ps`
- [ ] Containers sobem automaticamente após reboot
- [ ] Dados intactos após reboot

---

**Data de Criação**: 2025-11-14  
**Versão**: 1.0  
**Status**: ✅ PRODUÇÃO

