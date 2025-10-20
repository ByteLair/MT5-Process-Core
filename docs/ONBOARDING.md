# MT5 Trading System - Guia de Onboarding

Bem-vindo ao time! Este guia vai te ajudar a configurar o ambiente e fazer suas primeiras contribuições.

## Dia 1: Setup do Ambiente

### 1.1 Pré-requisitos

Certifique-se de ter instalado:

```bash
# Verificar versões
docker --version        # 20.10+
docker-compose --version # 1.29+
python --version        # 3.9+
git --version          # 2.30+
```

Se falta algo:

```bash
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER  # Adiciona seu usuário ao grupo docker
newgrp docker  # Ativa o grupo sem relogin

# Python
sudo apt-get update
sudo apt-get install python3.9 python3-pip python3-venv

# Git
sudo apt-get install git
```

### 1.2 Clone e Configure

```bash
# Clone o repositório
git clone https://github.com/Lysk-dot/mt5-trading-db.git
cd mt5-trading-db

# Configure seu git
git config user.name "Seu Nome"
git config user.email "seu.email@example.com"

# Crie um branch de trabalho
git checkout -b onboarding/seu-nome
```

### 1.3 Primeiro Build

```bash
# Inicie os containers
docker compose up -d

# Aguarde ~30 segundos e verifique o status
docker compose ps

# Todos devem estar "Up" e "healthy"
```

### 1.4 Verificação

```bash
# Health check
bash scripts/health-check.sh

# Acesse os serviços
echo "API: http://localhost:8001/docs"
echo "Grafana: http://localhost:3000 (admin/admin)"
echo "Prometheus: http://localhost:9090"
```

**✅ Checkpoint**: Todos os serviços devem estar rodando e acessíveis.

---

## Dia 2: Explorando o Sistema

### 2.1 Estrutura do Projeto

```
mt5-trading-db/
├── api/              # API REST (FastAPI)
│   ├── app/          # Aplicação principal
│   ├── tests/        # Testes da API
│   └── requirements.txt
├── ml/               # Machine Learning
│   ├── worker/       # Scripts de treinamento
│   ├── models/       # Modelos salvos
│   └── tests/        # Testes ML
├── db/               # Banco de dados
│   └── init/         # Scripts SQL de inicialização
├── scripts/          # Scripts de automação
│   └── tests/        # Testes de scripts
├── grafana/          # Dashboards e alertas
│   └── provisioning/
├── prometheus/       # Configuração de métricas
├── loki/             # Configuração de logs
├── systemd/          # Serviços e timers
└── docs/             # Documentação
```

### 2.2 Fluxo de Dados

1. **Ingestão**: MT5 → API `/ingest` → PostgreSQL
2. **Features**: SQL calcula indicadores técnicos
3. **Treinamento**: ML Worker → treina modelo → salva em `ml/models/`
4. **Predição**: API → carrega modelo → gera sinais
5. **Monitoramento**: Métricas → Prometheus → Grafana

### 2.3 Teste sua primeira requisição

```bash
# Health check da API
curl http://localhost:8001/health

# Documentação interativa
curl http://localhost:8001/docs

# Gerar sinais (se houver dados)
curl http://localhost:8001/signals?timeframe=M1
```

**✅ Checkpoint**: Você deve conseguir fazer requisições à API.

---

## Dia 3: Primeiro Código

### 3.1 Setup Python Local (opcional)

```bash
# Crie ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instale dependências
pip install -r api/requirements.txt
pip install pytest black flake8
```

### 3.2 Execute os Testes

```bash
# Testes da API
pytest api/tests/ -v

# Testes de scripts
pytest scripts/tests/ -v

# Todos os testes
pytest -v
```

### 3.3 Sua Primeira Mudança

Vamos adicionar um novo endpoint de exemplo:

```python
# api/app/main.py
@app.get("/welcome")
def welcome():
    return {"message": "Hello from onboarding!"}
```

```bash
# Reinicie a API
docker compose restart api

# Teste o novo endpoint
curl http://localhost:8001/welcome
```

### 3.4 Commit e Push

```bash
# Adicione e commite
git add api/app/main.py
git commit -m "feat: adiciona endpoint de boas-vindas"

# Push para seu branch
git push origin onboarding/seu-nome
```

**✅ Checkpoint**: Seu código está no GitHub!

---

## Dia 4: Entendendo ML

### 4.1 Dados e Features

```bash
# Conecte ao banco
docker exec -it mt5_db psql -U trader -d mt5_trading

# Explore os dados
\dt  -- Lista tabelas
SELECT COUNT(*) FROM market_data;
SELECT * FROM features_m1 LIMIT 5;
\q  -- Sair
```

### 4.2 Treinamento Manual

```bash
# Entre no container ML
docker compose exec ml bash

# Execute o treinamento
python ml/worker/train.py

# Verifique o modelo salvo
ls -lh ml/models/
cat ml/models/manifest.json

exit
```

### 4.3 Visualize Métricas

1. Abra Grafana: <http://localhost:3000>
2. Login: admin/admin
3. Dashboard: "MT5 ML/AI Dashboard"
4. Veja logs e métricas de treinamento

**✅ Checkpoint**: Você treinou e visualizou um modelo!

---

## Dia 5: Operações

### 5.1 Logs e Debugging

```bash
# Logs em tempo real
docker compose logs -f api

# Logs específicos
docker compose logs ml --tail=50

# Logs do Grafana/Loki
# Acesse http://localhost:3000 → Explore → Loki
```

### 5.2 Manutenção

```bash
# Status geral
bash scripts/maintenance.sh status

# Manutenção completa
bash scripts/maintenance.sh full

# Limpeza
bash scripts/maintenance.sh cleanup
```

### 5.3 Backup e Restore

```bash
# Backup local
bash scripts/backup.sh

# Restaurar (CUIDADO: sobrescreve dados)
# bash scripts/restore.sh backups/backup_YYYY-MM-DD.tar.gz
```

**✅ Checkpoint**: Você sabe operar o sistema!

---

## Próximos Passos

### Adicione um Novo Símbolo

1. Insira dados no banco via API `/ingest`
2. Verifique em `market_data`
3. Features são calculadas automaticamente
4. Modelo pode prever para o novo símbolo

### Crie um Novo Modelo ML

1. Adicione script em `ml/worker/`
2. Salve modelo em `ml/models/meu_modelo.pkl`
3. Atualize API para carregar seu modelo
4. Adicione testes em `ml/tests/`

### Adicione um Novo Endpoint

1. Defina rota em `api/app/main.py` ou novo módulo
2. Adicione validação (Pydantic models)
3. Documente com docstrings
4. Adicione testes em `api/tests/`
5. Atualize `docs/DOCUMENTATION.md`

### Melhore os Dashboards

1. Edite JSON em `grafana/provisioning/dashboards/`
2. Adicione painéis, queries, alertas
3. Teste no Grafana
4. Commite as mudanças

---

## Recursos

- **Documentação Completa**: `docs/DOCUMENTATION.md`
- **Diagramas**: `docs/DIAGRAMS.md`
- **FAQ**: `docs/FAQ.md`
- **Glossário**: `docs/GLOSSARY.md`
- **Runbook**: `docs/RUNBOOK.md`

---

## Checklist de Onboarding

- [ ] Ambiente configurado e rodando
- [ ] Executei os testes com sucesso
- [ ] Fiz meu primeiro commit
- [ ] Entendo o fluxo de dados
- [ ] Treinei um modelo ML
- [ ] Acessei Grafana e vi métricas
- [ ] Li a documentação completa
- [ ] Sei como debugar e operar o sistema

---

## Dúvidas?

- Revise a documentação em `docs/`
- Pergunte ao time no Slack/Discord
- Abra uma issue no GitHub
- Email: <kuramopr@gmail.com>

**Bem-vindo ao time! 🚀**
