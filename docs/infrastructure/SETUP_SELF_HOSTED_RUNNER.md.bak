# 🚀 CI/CD com GitHub Actions Self-hosted Runner

## 1️⃣ Instalar Runner no Servidor

```bash
# No seu servidor (ex: 192.168.15.20)
mkdir -p ~/actions-runner && cd ~/actions-runner

# Baixe a versão mais recente
curl -o actions-runner-linux-x64-2.311.0.tar.gz \
  -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# Extraia
tar xzf actions-runner-linux-x64-2.311.0.tar.gz
```

## 2️⃣ Registrar Runner no GitHub

- Vá em **Settings → Actions → Runners → New self-hosted runner** no seu repositório
- Escolha **Linux x64**
- Copie o comando de registro (vai ser algo como):

```bash
./config.sh --url https://github.com/Lysk-dot/mt5-trading-db --token SEU_TOKEN_AQUI
```

## 3️⃣ Iniciar Runner como Serviço

```bash
# Instale como serviço (systemd)
sudo ./svc.sh install
sudo ./svc.sh start

# Para verificar status:
sudo ./svc.sh status
```

## 4️⃣ Testar Runner

- No GitHub, o runner deve aparecer como **Online**
- Faça um commit/push para `main` e veja se o job roda no seu servidor

---

## 5️⃣ Workflow de Deploy

Crie o arquivo `.github/workflows/deploy.yml` no seu repositório:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: self-hosted  # Roda no seu servidor
    steps:
      - uses: actions/checkout@v4

      - name: Deploy
        run: |
          cd /home/felipe/mt5-trading-db
          git pull
          docker compose up -d api
```

---

## 6️⃣ Dicas de Segurança

- O runner tem acesso total ao servidor! Use apenas em ambientes confiáveis
- Mantenha o runner atualizado (`cd ~/actions-runner && ./bin/Runner.Listener --version`)
- Use usuário dedicado para o runner (ex: `github-runner`)
- Limite permissões do usuário runner
- Monitore logs: `~/actions-runner/_diag/`

---

## 7️⃣ Manutenção

- Para atualizar o runner:

```bash
cd ~/actions-runner
sudo ./svc.sh stop
rm -rf *
# Baixe nova versão e repita o setup
```

- Para remover:

```bash
cd ~/actions-runner
sudo ./svc.sh stop
sudo ./svc.sh uninstall
rm -rf ~/actions-runner
```

---

## 8️⃣ Referências

- [GitHub Actions Self-hosted Runner Docs](https://docs.github.com/en/actions/hosting-your-own-runners/about-self-hosted-runners)
- [Security Best Practices](https://docs.github.com/en/actions/hosting-your-own-runners/security-best-practices-for-self-hosted-runners)

---

**Pronto! Seu CI/CD vai rodar 100% no seu servidor, com deploy automático a cada push!**
