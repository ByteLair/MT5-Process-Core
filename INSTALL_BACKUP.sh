#!/usr/bin/env bash
################################################################################
# GUIA DE INSTALAÇÃO COMPLETO - SISTEMA DE BACKUP MT5 TRADING DB
################################################################################

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                                                                    ║"
echo "║   MT5 TRADING DB - SISTEMA DE BACKUP AUTOMÁTICO                   ║"
echo "║   Configuração Completa para Cliente e Servidor                   ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

cat << 'EOF'

📋 RESUMO DO QUE FOI CRIADO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCRIPTS:
  ✅ scripts/backup.sh              - Script principal de backup
  ✅ scripts/setup-backup.sh        - Instalador automático
  ✅ scripts/test-backup.sh         - Testes de conectividade

CONFIGURAÇÃO:
  ✅ .env.backup                    - Template de configuração
  ✅ systemd/mt5-backup.service     - Serviço systemd
  ✅ systemd/mt5-backup.timer       - Timer para backup diário

DOCUMENTAÇÃO:
  ✅ docs/backup.md                 - Documentação completa

REPOSITÓRIO GITHUB:
  ✅ .github/dependabot.yml         - Auto-update de dependências
  ✅ .github/codeql.yml             - Análise de segurança
  ✅ .github/ISSUE_TEMPLATE/        - Templates de issue
  ✅ .github/PULL_REQUEST_TEMPLATE  - Template de PR
  ✅ .github/CODEOWNERS             - Ownership de código

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 PASSO A PASSO - INSTALAÇÃO NO SERVIDOR MT5 (CLIENTE):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  EXECUTAR SCRIPT DE INSTALAÇÃO:
   
   cd /home/felipe/mt5-trading-db
   sudo ./scripts/setup-backup.sh

   O script irá:
   • Criar diretórios (/var/backups/mt5)
   • Instalar dependências (postgresql-client, curl, jq)
   • Copiar configuração para /etc/default/mt5-backup
   • Instalar serviços systemd
   • Habilitar timer de backup diário

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2️⃣  CONFIGURAR IP DO SERVIDOR DE BACKUP:

   sudo nano /etc/default/mt5-backup

   Altere a linha:
   BACKUP_API_URL=http://SEU_IP_BACKUP:9101
   
   Para (exemplo):
   BACKUP_API_URL=http://192.168.1.100:9101

   Salve (Ctrl+O, Enter, Ctrl+X)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

3️⃣  TESTAR CONECTIVIDADE:

   sudo ./scripts/test-backup.sh

   Este comando verifica:
   • Dependências instaladas ✅
   • Conexão com PostgreSQL ✅
   • Conexão com API remota ✅
   • Autenticação ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

4️⃣  EXECUTAR PRIMEIRO BACKUP DE TESTE:

   sudo systemctl start mt5-backup.service

   Verificar resultado:
   sudo journalctl -u mt5-backup.service -n 100

   Listar backups criados:
   ls -lh /var/backups/mt5/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PRONTO! O BACKUP ESTÁ CONFIGURADO!

   • Backups automáticos diários às 03:00 AM
   • Retenção local: 3 backups
   • Upload automático para servidor remoto
   • Verificação de integridade com SHA256

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 COMANDOS ÚTEIS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ver status do timer:
  systemctl status mt5-backup.timer

Executar backup manualmente:
  sudo systemctl start mt5-backup.service

Ver logs em tempo real:
  sudo journalctl -u mt5-backup.service -f

Listar backups locais:
  ls -lh /var/backups/mt5/

Verificar integridade de um backup:
  cd /var/backups/mt5
  sha256sum -c nome-do-backup.dump.sha256

Ver próxima execução agendada:
  systemctl list-timers mt5-backup.timer

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 CONFIGURAÇÃO AVANÇADA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Alterar horário do backup:
  sudo nano /etc/systemd/system/mt5-backup.timer
  Edite a linha: OnCalendar=*-*-* 03:00:00
  sudo systemctl daemon-reload
  sudo systemctl restart mt5-backup.timer

Alterar retenção local (número de backups):
  sudo nano /etc/default/mt5-backup
  Edite: KEEP_LOCAL_BACKUPS=5

Alterar número de tentativas de upload:
  sudo nano /etc/default/mt5-backup
  Edite: MAX_RETRIES=5

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 DOCUMENTAÇÃO COMPLETA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Leia a documentação completa em:
  cat docs/backup.md

Ou abra no navegador/editor de texto:
  xdg-open docs/backup.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 SEGURANÇA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Arquivo de configuração protegido: chmod 600 /etc/default/mt5-backup
• Token de autenticação único e seguro
• Recomendado: Use HTTPS em produção
• Backups locais com permissões restritas (root only)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🆘 SUPORTE E TROUBLESHOOTING:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Se encontrar problemas:

1. Execute teste de conectividade:
   sudo ./scripts/test-backup.sh

2. Verifique logs detalhados:
   sudo journalctl -u mt5-backup.service -n 200

3. Teste conexão com servidor remoto:
   curl http://SEU_IP:9101/health

4. Consulte documentação:
   cat docs/backup.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EOF

echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                                                                    ║"
echo "║   ✅ SISTEMA DE BACKUP CONFIGURADO COM SUCESSO!                    ║"
echo "║                                                                    ║"
echo "║   Próximo passo: Execute o instalador                             ║"
echo "║   sudo ./scripts/setup-backup.sh                                  ║"
echo "║                                                                    ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
