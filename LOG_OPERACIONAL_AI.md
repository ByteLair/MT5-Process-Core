# Documentação das Ações Realizadas (Outubro 2025)

## 1. Diagnóstico Inicial

- Verificação do status dos containers Docker (`docker ps -a`).
- Coleta de logs dos containers `api` e `db` para identificar problemas de saúde e dependências.
- Teste do endpoint `/health` da API para garantir conectividade com o banco de dados.

## 2. Ajuste de Dependências Python

- Atualização do `requirements.txt` da API para usar `psycopg2-binary==2.9.9` (compatibilidade com SQLAlchemy e TimescaleDB).
- Rebuild dos containers após ajuste de dependências.

## 3. Verificação e Correção de Modelos

- Checagem do diretório `/models/` no container da API.
- Identificação de ausência dos arquivos de modelo (`rf_m1.pkl` e `latest_model.pkl`).
- Geração de modelos de teste usando `scikit-learn` e `joblib` diretamente no container da API para permitir inicialização e health check.

## 4. Troubleshooting Docker

- Tentativas de reiniciar, parar e remover containers problemáticos usando:
  - `docker-compose down --remove-orphans`
  - `docker stop`, `docker rm`, `docker kill`
  - `systemctl restart docker`
  - `docker system prune -f`
- Adição do usuário ao grupo `docker` para resolver problemas de permissão.
- Orientação para reboot do servidor caso persistam problemas de permissão.

## 5. Recomendações Futuras

- Corrigir o schema da tabela `trade_logs` para garantir compatibilidade com hypertable (PRIMARY KEY incluindo `ts`).
- Atualizar a extensão TimescaleDB para a versão mais recente quando possível.
- Garantir que os modelos estejam sempre presentes em `/models/` para a API funcionar corretamente.

## 6. Próximos Passos Pós-Reboot

- Verificar status do Docker: `sudo systemctl status docker`
- Subir containers: `docker-compose up -d`
- Garantir presença dos modelos em `/models/`
- Corrigir schema do banco conforme necessário

---

**Observação:**
Todas as ações foram documentadas para facilitar troubleshooting futuro e garantir reprodutibilidade do ambiente.
