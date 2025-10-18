# 📊 MT5 Trading - SQL Queries Úteis

## Análise de Dados

### 1. Estatísticas Gerais

```sql
-- Total de registros e período coberto
SELECT 
    COUNT(*) as total_records,
    MIN(ts) as first_record,
    MAX(ts) as last_record,
    COUNT(DISTINCT symbol) as unique_symbols,
    COUNT(DISTINCT timeframe) as unique_timeframes
FROM market_data;
```

### 2. Dados por Símbolo

```sql
-- Contagem de registros por símbolo
SELECT 
    symbol,
    COUNT(*) as records,
    MIN(ts) as first_ts,
    MAX(ts) as last_ts,
    MAX(ts) - MIN(ts) as time_span
FROM market_data
GROUP BY symbol
ORDER BY records DESC
LIMIT 20;
```

### 3. Atividade Recente

```sql
-- Registros recebidos nas últimas horas
SELECT 
    symbol,
    timeframe,
    COUNT(*) FILTER (WHERE ts >= NOW() - INTERVAL '1 hour') as last_1h,
    COUNT(*) FILTER (WHERE ts >= NOW() - INTERVAL '6 hours') as last_6h,
    COUNT(*) FILTER (WHERE ts >= NOW() - INTERVAL '24 hours') as last_24h,
    MAX(ts) as last_update
FROM market_data
GROUP BY symbol, timeframe
HAVING COUNT(*) FILTER (WHERE ts >= NOW() - INTERVAL '24 hours') > 0
ORDER BY last_update DESC;
```

### 4. Gaps de Dados

```sql
-- Detectar gaps maiores que 5 minutos em M1
WITH gaps AS (
    SELECT 
        symbol,
        ts,
        LAG(ts) OVER (PARTITION BY symbol ORDER BY ts) as prev_ts,
        ts - LAG(ts) OVER (PARTITION BY symbol ORDER BY ts) as gap
    FROM market_data
    WHERE timeframe = 'M1'
)
SELECT 
    symbol,
    prev_ts,
    ts,
    gap,
    EXTRACT(EPOCH FROM gap)/60 as gap_minutes
FROM gaps
WHERE gap > INTERVAL '5 minutes'
ORDER BY gap DESC
LIMIT 50;
```

### 5. Análise de Volume

```sql
-- Volume médio, mínimo e máximo por símbolo
SELECT 
    symbol,
    AVG(volume) as avg_volume,
    MIN(volume) as min_volume,
    MAX(volume) as max_volume,
    STDDEV(volume) as stddev_volume
FROM market_data
WHERE timeframe = 'M1' 
  AND ts >= NOW() - INTERVAL '24 hours'
GROUP BY symbol
ORDER BY avg_volume DESC;
```

### 6. Volatilidade

```sql
-- Volatilidade (high-low) por símbolo nas últimas 24h
SELECT 
    symbol,
    COUNT(*) as candles,
    AVG(high - low) as avg_range,
    MAX(high - low) as max_range,
    MIN(high - low) as min_range,
    STDDEV(high - low) as stddev_range
FROM market_data
WHERE timeframe = 'M1'
  AND ts >= NOW() - INTERVAL '24 hours'
GROUP BY symbol
ORDER BY avg_range DESC
LIMIT 20;
```

### 7. Preço Atual vs Histórico

```sql
-- Comparação de preço atual com médias históricas
WITH current_prices AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        close as current_price,
        ts as last_update
    FROM market_data
    WHERE timeframe = 'M1'
    ORDER BY symbol, ts DESC
),
averages AS (
    SELECT 
        symbol,
        AVG(close) as avg_24h,
        AVG(close) FILTER (WHERE ts >= NOW() - INTERVAL '1 hour') as avg_1h
    FROM market_data
    WHERE timeframe = 'M1'
      AND ts >= NOW() - INTERVAL '24 hours'
    GROUP BY symbol
)
SELECT 
    c.symbol,
    c.current_price,
    a.avg_1h,
    a.avg_24h,
    ((c.current_price - a.avg_1h) / a.avg_1h * 100) as pct_change_1h,
    ((c.current_price - a.avg_24h) / a.avg_24h * 100) as pct_change_24h,
    c.last_update
FROM current_prices c
JOIN averages a ON c.symbol = a.symbol
ORDER BY ABS((c.current_price - a.avg_24h) / a.avg_24h) DESC
LIMIT 20;
```

## Performance e Otimização

### 8. Tamanho das Tabelas

```sql
-- Tamanho de cada tabela do banco
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### 9. Índices e Performance

```sql
-- Lista de índices e seus tamanhos
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) as size
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_relation_size(indexname::regclass) DESC;
```

### 10. Conexões Ativas

```sql
-- Listar conexões ativas ao banco
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    NOW() - query_start as query_duration,
    LEFT(query, 100) as query_preview
FROM pg_stat_activity
WHERE datname = 'mt5_trading'
  AND state != 'idle'
ORDER BY query_start;
```

## Manutenção

### 11. Vacuum e Análise

```sql
-- Status de vacuum e análise das tabelas
SELECT 
    schemaname,
    relname,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

### 12. Limpeza de Dados Antigos

```sql
-- CUIDADO: Delete registros mais antigos que 1 ano
-- Execute apenas se necessário e faça backup primeiro!
-- DELETE FROM market_data WHERE ts < NOW() - INTERVAL '1 year';

-- Melhor: Contar quantos registros seriam deletados
SELECT 
    COUNT(*) as records_to_delete,
    pg_size_pretty(COUNT(*) * 
        (SELECT pg_column_size(ROW(m.*)) FROM market_data m LIMIT 1)
    ) as estimated_space_freed
FROM market_data
WHERE ts < NOW() - INTERVAL '1 year';
```

### 13. Duplicatas

```sql
-- Verificar duplicatas (não deveria existir devido ao PK)
SELECT 
    symbol,
    timeframe,
    ts,
    COUNT(*) as duplicates
FROM market_data
GROUP BY symbol, timeframe, ts
HAVING COUNT(*) > 1
LIMIT 100;
```

## TimescaleDB Específico

### 14. Chunks (Hypertable)

```sql
-- Ver chunks da hypertable (se configurado)
SELECT 
    chunk_schema,
    chunk_name,
    range_start,
    range_end,
    pg_size_pretty(chunk_size) as chunk_size
FROM timescaledb_information.chunks
WHERE hypertable_name = 'market_data'
ORDER BY range_start DESC
LIMIT 20;
```

### 15. Continuous Aggregates

```sql
-- Listar continuous aggregates (se existirem)
SELECT 
    view_name,
    materialized_only,
    refresh_lag,
    refresh_interval
FROM timescaledb_information.continuous_aggregates;
```

## Machine Learning

### 16. Features para Treinamento

```sql
-- Extrair features para ML (últimas 10k linhas)
SELECT 
    symbol,
    timeframe,
    ts,
    open,
    high,
    low,
    close,
    volume,
    -- Features calculadas
    (close - open) as body,
    (high - low) as range,
    (high - GREATEST(open, close)) as upper_shadow,
    (LEAST(open, close) - low) as lower_shadow,
    -- Retornos
    (close - LAG(close, 1) OVER w) / NULLIF(LAG(close, 1) OVER w, 0) as ret_1,
    (close - LAG(close, 5) OVER w) / NULLIF(LAG(close, 5) OVER w, 0) as ret_5,
    -- Médias móveis
    AVG(close) OVER (PARTITION BY symbol, timeframe ORDER BY ts ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as ma_5,
    AVG(close) OVER (PARTITION BY symbol, timeframe ORDER BY ts ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as ma_20,
    -- Volatilidade
    STDDEV(close) OVER (PARTITION BY symbol, timeframe ORDER BY ts ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as volatility_20
FROM market_data
WHERE symbol = 'EURUSD' 
  AND timeframe = 'M1'
  AND ts >= NOW() - INTERVAL '7 days'
WINDOW w AS (PARTITION BY symbol, timeframe ORDER BY ts)
ORDER BY ts DESC
LIMIT 10000;
```

### 17. Target para Previsão

```sql
-- Criar target (retorno futuro) para treinamento
SELECT 
    symbol,
    timeframe,
    ts,
    close,
    -- Target: retorno após N períodos
    LEAD(close, 1) OVER w / close - 1 as target_ret_1,
    LEAD(close, 5) OVER w / close - 1 as target_ret_5,
    LEAD(close, 10) OVER w / close - 1 as target_ret_10,
    -- Classificação: direção do movimento
    CASE 
        WHEN LEAD(close, 1) OVER w > close THEN 1 
        ELSE 0 
    END as target_direction
FROM market_data
WHERE symbol = 'EURUSD'
  AND timeframe = 'M1'
  AND ts >= NOW() - INTERVAL '30 days'
WINDOW w AS (PARTITION BY symbol, timeframe ORDER BY ts)
ORDER BY ts DESC
LIMIT 50000;
```

## Monitoramento

### 18. Taxa de Inserção

```sql
-- Taxa de inserção por hora nas últimas 24h
SELECT 
    DATE_TRUNC('hour', ts) as hour,
    COUNT(*) as records_inserted,
    COUNT(DISTINCT symbol) as unique_symbols
FROM market_data
WHERE ts >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', ts)
ORDER BY hour DESC;
```

### 19. Qualidade dos Dados

```sql
-- Verificar qualidade dos dados (valores nulos, zero, outliers)
SELECT 
    symbol,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE open IS NULL) as null_open,
    COUNT(*) FILTER (WHERE high IS NULL) as null_high,
    COUNT(*) FILTER (WHERE low IS NULL) as null_low,
    COUNT(*) FILTER (WHERE close IS NULL) as null_close,
    COUNT(*) FILTER (WHERE volume IS NULL OR volume = 0) as null_or_zero_volume,
    COUNT(*) FILTER (WHERE high < low) as invalid_high_low,
    COUNT(*) FILTER (WHERE close < 0 OR close > 1000000) as outlier_close
FROM market_data
WHERE ts >= NOW() - INTERVAL '7 days'
GROUP BY symbol
ORDER BY (
    COALESCE(COUNT(*) FILTER (WHERE open IS NULL), 0) +
    COALESCE(COUNT(*) FILTER (WHERE high IS NULL), 0) +
    COALESCE(COUNT(*) FILTER (WHERE low IS NULL), 0) +
    COALESCE(COUNT(*) FILTER (WHERE close IS NULL), 0)
) DESC;
```

### 20. Última Atualização por Símbolo

```sql
-- Última atualização de cada símbolo/timeframe
SELECT 
    symbol,
    timeframe,
    MAX(ts) as last_update,
    NOW() - MAX(ts) as time_since_last_update,
    COUNT(*) as total_records
FROM market_data
GROUP BY symbol, timeframe
ORDER BY MAX(ts) DESC;
```

## Exportação

### 21. Exportar para CSV

```sql
-- Exportar dados para CSV (executar via psql com \copy)
-- \copy (SELECT * FROM market_data WHERE symbol = 'EURUSD' AND timeframe = 'M1' AND ts >= NOW() - INTERVAL '7 days') TO '/tmp/eurusd_m1_7days.csv' CSV HEADER;

-- Alternativa: gerar comando de exportação
SELECT 
    format(
        E'\\copy (SELECT * FROM market_data WHERE symbol = ''%s'' AND timeframe = ''%s'' AND ts >= NOW() - INTERVAL ''7 days'') TO ''/tmp/%s_%s_7days.csv'' CSV HEADER;',
        symbol,
        timeframe,
        LOWER(symbol),
        LOWER(timeframe)
    ) as export_command
FROM (SELECT DISTINCT symbol, timeframe FROM market_data ORDER BY symbol, timeframe) sub;
```

---

## 💡 Dicas de Uso

### Via Docker:
```bash
# Executar query via docker exec
docker exec mt5_db psql -U trader -d mt5_trading -c "SELECT COUNT(*) FROM market_data;"

# Executar query de arquivo
docker exec -i mt5_db psql -U trader -d mt5_trading < query.sql

# Modo interativo
docker exec -it mt5_db psql -U trader -d mt5_trading
```

### Via pgAdmin:
1. Acesse http://localhost:5051
2. Adicione servidor (Host: db, Port: 5432, User: trader, DB: mt5_trading)
3. Cole e execute as queries acima

### Performance:
- Use `EXPLAIN ANALYZE` antes de queries complexas
- Adicione índices se necessário
- Use `LIMIT` para queries exploratórias
- TimescaleDB otimiza automaticamente queries por timestamp

---

**Nota**: Sempre faça backup antes de executar comandos DELETE ou UPDATE!
