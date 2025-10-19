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

Siga as instruções fornecidas separadamente para configurar a API de recepção na porta 9101.

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

### Métricas Importantes

1. **Taxa de Sucesso**: % de backups bem-sucedidos
2. **Tempo de Execução**: Duração do backup
3. **Tamanho do Backup**: Crescimento ao longo do tempo
4. **Uso de Disco**: Espaço disponível
5. **Upload Remoto**: Taxa de sucesso de upload

### Alertas Recomendados

Configure alertas para:
- ❌ Falha de backup por 2 dias consecutivos
- ⚠️ Backup demorando > 30 minutos
- ⚠️ Espaço em disco < 20%
- ❌ Upload remoto falhando por 3 dias

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
