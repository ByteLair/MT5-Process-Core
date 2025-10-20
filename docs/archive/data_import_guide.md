# Guia de Importação de Dados Históricos

## Data: 2024-10-17

### Objetivo

Alimentar o banco de dados TimescaleDB com dados históricos de candles para treinar o modelo de ML.

## Processo de Importação

### 1. Preparação do Ambiente

#### Pacotes Python Instalados no Container

```bash
docker exec -it mt5_api pip install pandas sqlalchemy psycopg2-binary
```

**Nota**: Os pacotes devem ser instalados **dentro do container**, não no host.

### 2. Configuração de Volumes

O `docker-compose.yml` foi atualizado para montar os volumes necessários:

```yaml
api:
  volumes:
    - ./scripts:/app/scripts:ro
    - ./dados_historicos.csv:/app/scripts/dados_historicos.csv:ro
```

Após atualizar, reiniciar o container:

```bash
docker-compose restart api
```

### 3. Script de Importação

O script `scripts/import_csv.py` foi corrigido para:

- **Gerar coluna `ts`** a partir de `Date` e `Time` do CSV
- **Converter `ts` para datetime UTC** (compatível com `TIMESTAMPTZ` do Postgres)
- **Remover colunas extras** (`date`, `time`) antes da inserção
- **Inserir em lotes de 500 registros** para evitar excesso de parâmetros
- **Usar método padrão do pandas** (`to_sql` sem `method="multi"`)

#### Código Principal do Script

```python
#!/usr/bin/env python3
import os, sys, pandas as pd
from sqlalchemy import create_engine

# Parse args
csv_path = sys.argv[1]
symbol = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
timeframe = sys.argv[3] if len(sys.argv) > 3 else "M1"

# DB connection
db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://trader:trader123@localhost:5432/mt5_trading")
engine = create_engine(db_url, future=True)

# Read and normalize CSV
df = pd.read_csv(csv_path)
df.columns = [c.lower() for c in df.columns]

# Generate ts from date+time
if "ts" not in df.columns and "date" in df.columns and "time" in df.columns:
    df["ts"] = pd.to_datetime(df["date"] + " " + df["time"], format="%Y.%m.%d %H:%M", utc=True)

# Ensure ts is datetime
if not pd.api.types.is_datetime64_any_dtype(df["ts"]):
    df["ts"] = pd.to_datetime(df["ts"], utc=True)

# Add symbol/timeframe
df["symbol"] = symbol
df["timeframe"] = timeframe
if "spread" not in df.columns:
    df["spread"] = 0.0

# Remove extra columns
for col in ["date", "time"]:
    if col in df.columns:
        df.drop(columns=[col], inplace=True)

# Batch insert
chunksize = 500
cols = ["ts", "open", "high", "low", "close", "volume", "spread", "symbol", "timeframe"]
with engine.begin() as conn:
    for i in range(0, len(df), chunksize):
        chunk = df.iloc[i:i+chunksize].copy()
        chunk = chunk[cols]
        chunk.to_sql("market_data", conn, schema="public", index=False, if_exists="append")

print(f"imported rows: {len(df)}")
```

### 4. Execução da Importação

```bash
docker exec -it mt5_api bash -c "python3 /app/scripts/import_csv.py /app/scripts/dados_historicos.csv EURUSD H1"
```

**Resultado**: 24.882 linhas importadas com sucesso para `public.market_data`.

## Erros Resolvidos Durante o Processo

### 1. Coluna `ts` Faltando

**Erro**: `missing columns: {'ts'}`
**Solução**: Gerar `ts` a partir de `Date` e `Time`.

### 2. Colunas Extras no DataFrame

**Erro**: `Columns in DataFrame but not in table: {'date', 'time'}`
**Solução**: Remover colunas extras antes da inserção.

### 3. Excesso de Parâmetros no SQLAlchemy

**Erro**: `(psycopg.errors.ProgramLimitExceeded)`
**Solução**: Reduzir batch size de 5000 para 500 e remover `method="multi"`.

### 4. Tipo de Coluna `ts` Incompatível

**Erro**: `column "ts" is of type timestamp with time zone but expression is of type character varying`
**Solução**: Converter `ts` para `datetime64[ns, UTC]` antes da inserção.

## Validação dos Dados

Para verificar os dados importados:

```sql
-- Contar registros
SELECT COUNT(*) FROM public.market_data WHERE symbol = 'EURUSD' AND timeframe = 'H1';

-- Ver range temporal
SELECT MIN(ts), MAX(ts) FROM public.market_data WHERE symbol = 'EURUSD' AND timeframe = 'H1';

-- Amostra dos dados
SELECT * FROM public.market_data WHERE symbol = 'EURUSD' AND timeframe = 'H1' ORDER BY ts DESC LIMIT 10;
```

## Próximos Passos

1. **Validar qualidade dos dados** importados
2. **Executar feature engineering** (gerar indicadores técnicos)
3. **Treinar modelo de ML** com os dados históricos
4. **Avaliar performance** do modelo
5. **Deploy do modelo** para predição em tempo real

## Referências

- Arquivo CSV: `dados_historicos.csv` (24.882 candles, EURUSD H1)
- Script: `scripts/import_csv.py`
- Tabela destino: `public.market_data`
- Container: `mt5_api`
