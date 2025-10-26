# Terraform Provisioning - Status

## Provisionamento Concluído ✅

O Terraform provisionou com sucesso um container TimescaleDB/PostgreSQL:

- **Nome:** `mt5_db_tf`
- **Imagem:** `timescale/timescaledb:2.14.2-pg16`
- **Porta externa:** `5433` (para evitar conflito com o container existente na porta 5432)
- **Porta interna:** `5432`
- **Credenciais:**
  - Usuário: `trader`
  - Senha: <definida via variável de ambiente>
  - Banco: `mt5_trading`

## Como acessar

```bash
psql -h localhost -p 5433 -U trader -d mt5_trading
```

Ou via URL de conexão:

```
postgresql+psycopg://trader:<senha>@localhost:5433/mt5_trading
```

## Gerenciamento

- **Ver recursos:** `terraform show`
- **Destruir recursos:** `terraform destroy`
- **Ver estado:** `terraform state list`

---

# ENGLISH

## Provisioning Completed ✅

Terraform successfully provisioned a TimescaleDB/PostgreSQL container:

- **Name:** `mt5_db_tf`
- **Image:** `timescale/timescaledb:2.14.2-pg16`
- **External port:** `5433` (to avoid conflict with existing container on port 5432)
- **Internal port:** `5432`
- **Credentials:**
  - User: `trader`
  - Password: <set via environment variable>
  - Database: `mt5_trading`

## How to access

```bash
psql -h localhost -p 5433 -U trader -d mt5_trading
```

Or via connection URL:

```
postgresql+psycopg://trader:<password>@localhost:5433/mt5_trading
```

## Management

- **View resources:** `terraform show`
- **Destroy resources:** `terraform destroy`
- **View state:** `terraform state list`
