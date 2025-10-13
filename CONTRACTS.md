# CONTRACTS.md

## Auth
- Header obrigatório: `X-API-Key: <chave>` em todas as rotas.
- CORS controlado por `ALLOW_ORIGINS`.

## Endpoints
### GET /health
- 200: `{"status":"ok"}`

### GET /predict
- Query: `symbol` (str), `limit` (int, default 30)
- 200: `{"symbol": "...", "n": 30, "prob_up_latest": 0.55, "ts_latest": "..."}`
- 404 se não houver dados.
- 401 sem API key. 429 em rate limit.

## Banco
- `public.market_data(symbol,timeframe,ts)` PK.
- Views: `features_m1`, `labels_m1`, `trainset_m1`.
- Tabela de saída: `public.signals`.

## Usuários e permissões
- Role `mt5_app` com privilégios mínimos (ver `db/init/03-roles.sql`).
- Conexão da API deve usar `mt5_app`.

## Políticas Timescale
- Compressão e retenção configuradas em init SQL.
- Verificar jobs em `timescaledb_information.jobs` após subir