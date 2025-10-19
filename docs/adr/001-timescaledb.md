# ADR-001: Uso de TimescaleDB para Dados de Trading

**Status**: ✅ Aceito  
**Data**: 2025-01-15  
**Autor**: Equipe MT5 Trading  
**Decisores**: Arquitetos de Sistema, DBA, Desenvolvedores Backend

## Contexto

O sistema precisa armazenar grandes volumes de dados de trading com timestamped data (candles OHLCV, ticks, spreads). Os requisitos incluem:

- **Alta volumetria**: Milhões de registros de dados de mercado por dia
- **Time-series queries**: Agregações temporais frequentes (médias, somas por período)
- **Retenção de dados**: Manter dados históricos para análise e backtesting
- **Performance de escrita**: Ingestão de dados em tempo real com baixa latência
- **Queries complexas**: JOINs com features calculadas, ML training data
- **Manutenção**: Compressão automática e políticas de retenção

## Decisão

Adotar **TimescaleDB** como banco de dados principal para armazenar dados de trading.

TimescaleDB é uma extensão PostgreSQL otimizada para time-series data que oferece:
- Hypertables: particionamento automático por tempo
- Compression: redução de storage em dados históricos
- Continuous aggregates: views materializadas incrementais
- Data retention policies: remoção automática de dados antigos
- Compatibilidade total com PostgreSQL: SQL completo, ecosystem de ferramentas

## Alternativas Consideradas

### Alternativa 1: InfluxDB
- **Prós**: 
  - Projetado especificamente para time-series
  - Alta performance de escrita
  - Compressão eficiente
- **Contras**: 
  - InfluxQL/Flux não são SQL padrão (curva de aprendizado)
  - Limitações em queries complexas e JOINs
  - Ecosystem menor que PostgreSQL
  - Dificuldade para ML workloads (precisa exportar dados)

### Alternativa 2: PostgreSQL Vanilla
- **Prós**: 
  - SQL completo
  - Ecosystem robusto
  - Familiaridade da equipe
- **Contras**: 
  - Performance inferior em queries time-series
  - Particionamento manual complexo
  - Sem compressão automática
  - Sem continuous aggregates

### Alternativa 3: MongoDB
- **Prós**: 
  - Flexibilidade de schema
  - Escalabilidade horizontal
- **Contras**: 
  - Não otimizado para time-series
  - Queries agregadas menos eficientes
  - Curva de aprendizado para NoSQL
  - Dificuldade para garantir consistência transacional

## Consequências

### Positivas

- ✅ **Performance**: Queries time-series 10-100x mais rápidas que PostgreSQL vanilla
- ✅ **Compressão**: Redução de 90%+ no storage com compression policies
- ✅ **SQL Completo**: Equipe já conhece PostgreSQL, zero curva de aprendizado
- ✅ **ML Pipeline**: Fácil integração com pandas, scikit-learn (SQLAlchemy)
- ✅ **Ecosystem**: pgAdmin, pg_dump, extensões PostgreSQL funcionam normalmente
- ✅ **Continuous Aggregates**: Features pré-calculadas para ML (RSI, MACD, etc.)
- ✅ **Manutenção Automática**: Políticas de retenção e compressão sem intervenção manual

### Negativas

- ❌ **Vertical Scaling**: Limitações de escalabilidade horizontal (mitigado: volume atual comporta single-node)
- ❌ **RAM Usage**: Compression/decompression requer mais RAM
- ❌ **Lock-in**: Migração futura para outro DB exige retrabalho

### Riscos

- ⚠️ **Crescimento de Dados**: Se volume ultrapassar capacidade single-node, precisará arquitetura distribuída
  - **Mitigação**: Monitorar crescimento, implementar retention policies agressivas
- ⚠️ **Versão TimescaleDB**: Breaking changes entre major versions
  - **Mitigação**: Testar upgrades em staging, manter documentação de versões

## Detalhes de Implementação

### Hypertable Principal

```sql
CREATE TABLE market_data (
    ts TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    spread DOUBLE PRECISION
);

SELECT create_hypertable('market_data', 'ts');
CREATE INDEX idx_market_data_symbol_timeframe ON market_data (symbol, timeframe, ts DESC);
```

### Compression Policy

```sql
ALTER TABLE market_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,timeframe'
);

SELECT add_compression_policy('market_data', INTERVAL '7 days');
```

### Continuous Aggregate (Features)

```sql
CREATE MATERIALIZED VIEW features_m1 
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', ts) AS ts_bucket,
    symbol,
    LAST(close, ts) AS close,
    AVG(volume) AS avg_volume,
    -- Mais features calculadas
FROM market_data
WHERE timeframe = 'M1'
GROUP BY ts_bucket, symbol;

SELECT add_continuous_aggregate_policy('features_m1',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');
```

### Retention Policy

```sql
SELECT add_retention_policy('market_data', INTERVAL '365 days');
```

## Referências

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [TimescaleDB vs InfluxDB Benchmark](https://blog.timescale.com/blog/timescaledb-vs-influxdb-for-time-series-data-timescale-influx-sql-nosql-36489299877/)
- [PostgreSQL + TimescaleDB for Financial Data](https://www.timescale.com/blog/how-to-store-financial-tick-data-in-postgresql/)
- Benchmark interno: `docs/benchmarks/timescaledb_performance.md`
