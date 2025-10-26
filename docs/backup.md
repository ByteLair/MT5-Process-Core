# MT5 Trading DB - Backup System Documentation

## 📚 Visão Geral

Sistema completo de backup automatizado para o banco de dados MT5 Trading, com:

- ✅ Backup local comprimido com `pg_dump`
- ✅ Checksum SHA256 para verificação de integridade
- ✅ Upload automático para servidor remoto via API REST
- ✅ Retry logic com exponential backoff
- ✅ Rotação automática de backups antigos
- ✅ Agendamento via systemd timer
- ✅ Logging estruturado e detalhado

---

## 🚀 Instalação Rápida

### No Servidor MT5 (Cliente)

```bash
# 1. Tornar scripts executáveis
chmod +x scripts/setup-backup.sh
chmod +x scripts/backup.sh
chmod +x scripts/test-backup.sh

# 2. Executar instalação
sudo ./scripts/setup-backup.sh

# 3. Configurar IP do servidor de backup
sudo nano /etc/default/mt5-backup
# Altere: BACKUP_API_URL=http://SEU_IP_BACKUP:9101

# 4. Testar conectividade
sudo ./scripts/test-backup.sh

# 5. Executar primeiro backup
sudo systemctl start mt5-backup.service
```

### No Servidor de Backup (Receptor)

Você pode executar a API de recepção (FastAPI + Uvicorn) no Linux como serviço de usuário systemd, escutando na porta 9101.

#### Instalação (API de Backup no Linux)

```bash
# Pré-requisitos: venv com dependências instaladas (já incluso no repo)
# Se necessário, instale dependências da API:
pip install -r api/requirements.txt

# Criar diretório de logs
mkdir -p ~/mt5-trading-db/logs/api

# Instalar o unit do serviço (modo usuário)
mkdir -p ~/.config/systemd/user
cp systemd/mt5-backup-api.service ~/.config/systemd/user/

# Recarregar, habilitar e iniciar
systemctl --user daemon-reload
systemctl --user enable --now mt5-backup-api.service

# Iniciar automaticamente após reboot (user lingering)
loginctl enable-linger "$USER"

# Abrir firewall (se UFW estiver ativo)
sudo ufw allow 9101/tcp
```

#### Verificação

```bash
# Status do serviço
systemctl --user status mt5-backup-api.service --no-pager

# Health local
curl http://127.0.0.1:9101/health

# Health remoto (de outra máquina da rede)
curl http://SEU_IP_LINUX:9101/health
```

#### Logs e Diagnóstico

```bash
# Logs do serviço
journalctl --user -u mt5-backup-api.service -f

# Logs de aplicação
tail -f ~/mt5-trading-db/logs/api/api.log

# Ver porta e processo
ss -ltnp | grep 9101
```

Notas:

- O app usa por padrão `LOG_DIR=./logs/api/` (ajustável via env). Evita permissões em `/app`.
- O serviço executa uvicorn a partir do venv local: `~/.venv/bin/uvicorn`.
- Em produção, recomende HTTPS atrás de um reverse proxy (nginx/caddy) e autenticação por token para endpoints de upload.

---

## ⚙️ Configuração

### Variáveis de Ambiente

Arquivo: `/etc/default/mt5-backup`

```bash
# Database
POSTGRES_DB=mt5_trading
POSTGRES_USER=trader
POSTGRES_PASSWORD=trader123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Local Backup
BACKUP_DIR=/var/backups/mt5
KEEP_LOCAL_BACKUPS=3

# Remote Backup Server
BACKUP_API_URL=http://192.168.1.100:9101
BACKUP_API_TOKEN=mt5-backup-secure-token-2025

# Upload Settings
MAX_RETRIES=3
RETRY_DELAY=5
```

### Agendamento

O backup é executado automaticamente **todos os dias às 03:00 AM** via systemd timer.

Para alterar o horário, edite: `/etc/systemd/system/mt5-backup.timer`

```ini
[Timer]
OnCalendar=*-*-* 03:00:00  # Formato: HH:MM:SS
```

Após editar, recarregue:

```bash
sudo systemctl daemon-reload
sudo systemctl restart mt5-backup.timer
```

---

## 📝 Uso

### Health Check do Endpoint Remoto

Antes de executar o backup, o script verifica automaticamente se o endpoint remoto (API de backup) está saudável.
Se o endpoint não responder com status OK, o backup é abortado e um erro é registrado nos logs.

**Como funciona:**

1. O script faz uma requisição HTTP para `$BACKUP_API_URL/health`.
2. Se a resposta for `{"status":"ok"}`, o backup prossegue normalmente.
3. Se não houver resposta ou o status for diferente, o backup não é executado.

**Exemplo de comando manual:**

```bash
curl -sS --max-time 5 $BACKUP_API_URL/health
```

**Logs:**

```bash
sudo journalctl -u mt5-backup.service -n 100 | grep health
```

**Importante:**

- Certifique-se que o servidor de destino está ativo e ouvindo na porta correta.
- O health check é obrigatório para evitar perda de backup ou uploads para destino errado.

### Executar Backup Manualmente

```bash
sudo systemctl start mt5-backup.service
```

### Ver Status do Timer

```bash
systemctl status mt5-backup.timer
systemctl list-timers mt5-backup.timer
```

### Ver Logs

```bash
# Logs do systemd (últimas 100 linhas)
sudo journalctl -u mt5-backup.service -n 100

# Logs detalhados em arquivo
sudo tail -f /var/backups/mt5/logs/*.log

# Log do último backup
ls -t /var/backups/mt5/logs/*.log | head -n1 | xargs cat
```

### Listar Backups Locais

```bash
ls -lh /var/backups/mt5/
ls -lh /var/backups/mt5/*.dump
```

### Verificar Integridade de Backup

```bash
cd /var/backups/mt5
sha256sum -c mt5_trading-20251019-030000.dump.sha256
```

---

## 🔄 Fluxo de Backup

```
┌─────────────────────────────────────────────────────────┐
│ 1. Timer Dispara (03:00 AM diariamente)                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Backup Local (pg_dump -Fc -Z9)                      │
│    → mt5_trading-20251019-030000.dump                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Gerar Checksum SHA256                               │
│    → mt5_trading-20251019-030000.dump.sha256            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Verificar Integridade                               │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Upload para Servidor Remoto (API REST)              │
│    POST /api/backup/upload                              │
│    → Retry até 3x em caso de falha                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Rotação de Backups Locais                           │
│    → Mantém últimos 3 backups                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 7. Log de Resultado                                     │
└─────────────────────────────────────────────────────────┘
```

---

## 🧪 Testes

### Teste de Conectividade

```bash
sudo ./scripts/test-backup.sh
```

Este script verifica:

- ✅ Dependências instaladas
- ✅ Diretórios e permissões
- ✅ Conexão com PostgreSQL
- ✅ Conexão com API remota
- ✅ Autenticação com token
- ✅ Status do systemd timer

### Teste de Backup Completo

```bash
# Executar backup de teste
sudo systemctl start mt5-backup.service

# Acompanhar execução
sudo journalctl -u mt5-backup.service -f

# Verificar resultado
ls -lh /var/backups/mt5/
```

---

## 🔐 Segurança

### Proteção de Credenciais

```bash
# Arquivo de configuração protegido
sudo chmod 600 /etc/default/mt5-backup
sudo chown root:root /etc/default/mt5-backup
```

### Token de Autenticação

O token de autenticação deve ser:

- ✅ Único e complexo
- ✅ Armazenado de forma segura
- ✅ Sincronizado entre cliente e servidor
- ✅ Rotacionado periodicamente

### Comunicação

⚠️ **Recomendação**: Use HTTPS em produção!

Para configurar HTTPS:

1. Obtenha certificado SSL (Let's Encrypt)
2. Configure nginx/caddy como reverse proxy
3. Atualize `BACKUP_API_URL` para usar `https://`

---

## 🚨 Troubleshooting

### Problema: Backup não executa automaticamente

```bash
# Verificar se timer está ativo
systemctl status mt5-backup.timer

# Se não estiver, habilitar
sudo systemctl enable mt5-backup.timer
sudo systemctl start mt5-backup.timer
```

### Problema: Falha na conexão com PostgreSQL

```bash
# Testar conexão manualmente
pg_isready -h localhost -p 5432 -U trader

# Verificar credenciais em /etc/default/mt5-backup
sudo nano /etc/default/mt5-backup
```

### Problema: Upload remoto falha

```bash
# Testar conectividade com API
curl http://SEU_IP:9101/health

# Testar autenticação
curl -H "Authorization: Bearer SEU_TOKEN" \
     http://SEU_IP:9101/api/backup/list

# Verificar logs detalhados
sudo journalctl -u mt5-backup.service -n 200
```

### Problema: Espaço em disco insuficiente

```bash
# Verificar espaço disponível
df -h /var/backups/mt5

# Reduzir retenção local
sudo nano /etc/default/mt5-backup
# Altere: KEEP_LOCAL_BACKUPS=2

# Limpar backups antigos manualmente
sudo rm /var/backups/mt5/*.dump.old
```

### Problema: Backup muito lento

```bash
# Verificar se compressão está causando lentidão
# Editar backup.sh e reduzir nível de compressão
# Linha: pg_dump ... -Z9 ...
# Alterar para: -Z6 (mais rápido, menos compressão)
```

---

## 📊 Monitoramento

### Integração com Grafana/Prometheus

O sistema exporta métricas de backup em formato Prometheus para integração direta com Grafana:

- Script: `scripts/backup-metrics-exporter.sh`
- Arquivo de métricas: `/var/backups/mt5/backup_metrics.prom`

Exemplo de métricas:

```
# HELP mt5_backup_status 1=success, 0=failure
mt5_backup_status 1
# HELP mt5_backup_db_size_bytes Size of last DB dump in bytes
mt5_backup_db_size_bytes 27998
# HELP mt5_backup_repo_size_bytes Size of last repo backup in bytes
mt5_backup_repo_size_bytes 91740440
# HELP mt5_backup_duration_seconds Duration of last backup in seconds
mt5_backup_duration_seconds 1
# HELP mt5_backup_last_timestamp ISO8601 timestamp of last backup
mt5_backup_last_timestamp{ts="2025-10-19T17:19:17+00:00"} 1
```

Basta configurar o Prometheus para coletar esse arquivo e criar dashboards no Grafana.

### Integração com Log Centralizado (ELK/Graylog)

Os logs detalhados dos backups são salvos em `/var/backups/mt5/logs/`. Para integração com ELK (Elasticsearch, Logstash, Kibana) ou Graylog:

- Use Filebeat, rsyslog ou outro agente para enviar os arquivos de log para o servidor de log centralizado.
- Exemplo de configuração Filebeat:

  ```yaml
  filebeat.inputs:
    - type: log
      paths:
        - /var/backups/mt5/logs/*.log
  output.elasticsearch:
    hosts: ["http://SEU_ELK:9200"]
  ```

- Para Graylog, configure o agente para enviar via GELF ou syslog.

### Fluxo Semanal Completo

O fluxo semanal executa, em sequência:

1. Backup do banco de dados (`scripts/backup.sh`)
2. Backup completo do repositório (`scripts/backup-full-repo.sh`)
3. Monitoramento do backup (`scripts/monitor-backup.sh`)
4. Exportação de métricas Prometheus (`scripts/backup-metrics-exporter.sh`)

Tudo é automatizado via systemd (`mt5-backup.service` e `mt5-backup.timer`).

---

## 🔄 Restauração

### Restaurar do Backup Local

```bash
# 1. Parar serviços que usam o banco
docker-compose down

# 2. Restaurar backup
pg_restore -h localhost -p 5432 -U trader -d mt5_trading \
  --clean --if-exists \
  /var/backups/mt5/mt5_trading-20251019-030000.dump

# 3. Reiniciar serviços
docker-compose up -d
```

### Restaurar do Backup Remoto

```bash
# 1. Baixar backup do servidor remoto
curl -H "Authorization: Bearer TOKEN" \
  http://SEU_IP:9101/api/backup/download/BACKUP_ID \
  -o backup.dump

# 2. Verificar integridade
sha256sum -c backup.dump.sha256

# 3. Restaurar (mesmo processo acima)
```

---

## 📈 Manutenção

### Verificação Mensal

- [ ] Testar restauração de backup
- [ ] Verificar integridade de backups remotos
- [ ] Revisar logs de erros
- [ ] Verificar espaço em disco
- [ ] Validar rotação de backups

### Auditoria Trimestral

- [ ] Revisar política de retenção
- [ ] Atualizar tokens de autenticação
- [ ] Testar disaster recovery completo
- [ ] Documentar mudanças e melhorias

---

## 📞 Suporte

Para problemas ou dúvidas:

1. Verifique os logs: `journalctl -u mt5-backup.service`
2. Execute teste: `./scripts/test-backup.sh`
3. Consulte a documentação do projeto

---

## 📄 Arquivos do Sistema

```
mt5-trading-db/
├── scripts/
│   ├── backup.sh              # Script principal de backup
│   ├── setup-backup.sh        # Script de instalação
│   └── test-backup.sh         # Script de testes
├── systemd/
│   ├── mt5-backup.service     # Serviço systemd
│   └── mt5-backup.timer       # Timer para agendamento
├── .env.backup                # Template de configuração
└── docs/
    └── backup.md              # Esta documentação

/etc/default/
└── mt5-backup                 # Configuração em produção

/var/backups/mt5/
├── *.dump                     # Arquivos de backup
├── *.sha256                   # Checksums
└── logs/                      # Logs detalhados
```

---

**Versão**: 1.0.0
**Última atualização**: 2025-10-19
