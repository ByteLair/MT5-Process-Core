# 🧪 Guia de Testes - MT5 Process Core

**Versão:** 1.0  
**Data:** Novembro 2025  
**Última Atualização:** 13/11/2025

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Estrutura dos Testes](#estrutura-dos-testes)
3. [Executando os Testes](#executando-os-testes)
4. [Fixtures Disponíveis](#fixtures-disponíveis)
5. [Criando Novos Testes](#criando-novos-testes)
6. [Markers e Categorias](#markers-e-categorias)
7. [Cobertura de Código](#cobertura-de-código)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## 📊 Visão Geral

### Status Atual

- **Total de Testes:** 127
- **Passando:** 74 (58%)
- **Falhando:** 52 (41%)
- **Cobertura:** 26%

### Módulos de Teste

```
api/tests/
├── conftest.py              # Fixtures compartilhadas (230 linhas)
├── test_api_endpoints.py    # 24 testes - API REST
├── test_database.py         # 24 testes - PostgreSQL
├── test_integration.py      # 11 testes - E2E workflows
├── test_validation.py       # 40 testes - Validação de dados
├── test_metrics.py          # 30 testes - Prometheus metrics
└── test_status.py           # 48 testes - Health checks
```

### Cobertura por Módulo

| Módulo | Statements | Cobertura | Status |
|--------|-----------|-----------|--------|
| `metrics.py` | 21 | 90% | ⭐⭐⭐ |
| `main.py` | 105 | 71% | ⭐⭐ |
| `signals.py` | 42 | 55% | ⭐ |
| `ingest.py` | 285 | 31% | 🔴 |
| `indicators_worker.py` | 103 | 0% | ❌ |
| `tick_aggregator.py` | 67 | 0% | ❌ |
| `predict.py` | 45 | 0% | ❌ |

---

## 🏗️ Estrutura dos Testes

### Organização

```python
# Estrutura padrão de um módulo de teste
"""
Descrição do módulo de teste.
"""
import pytest
from fastapi.testclient import TestClient


class TestNomeDaFuncionalidade:
    """Testes para funcionalidade X."""
    
    def test_caso_basico(self, test_client: TestClient):
        """Testa comportamento básico."""
        response = test_client.get("/endpoint")
        assert response.status_code == 200
    
    def test_caso_erro(self, test_client: TestClient):
        """Testa tratamento de erro."""
        response = test_client.post("/endpoint", json={})
        assert response.status_code == 422
```

### Convenções de Nomenclatura

- **Arquivos:** `test_*.py`
- **Classes:** `Test*`
- **Métodos:** `test_*`
- **Fixtures:** sem prefixo `test_`

### Estrutura AAA

Todos os testes seguem o padrão **Arrange-Act-Assert**:

```python
def test_exemplo(self, test_client: TestClient):
    # Arrange - Preparação
    data = {"symbol": "EURUSD", "price": 1.0950}
    
    # Act - Ação
    response = test_client.post("/endpoint", json=data)
    
    # Assert - Verificação
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

---

## 🚀 Executando os Testes

### Comandos Básicos

```bash
# Todos os testes
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v

# Testes específicos
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/test_api_endpoints.py -v

# Um teste específico
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/test_api_endpoints.py::TestHealthEndpoint::test_health_check -v
```

### Com Cobertura

```bash
# Cobertura completa
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v \
  --cov=app \
  --cov-report=html \
  --cov-report=term-missing

# Ver relatório HTML
docker cp mt5_api:/app/htmlcov ./htmlcov
xdg-open htmlcov/index.html

# Ou usando Firefox
firefox htmlcov/index.html
```

### Filtros e Seleção

```bash
# Por marker
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v -m slow
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v -m integration

# Por palavra-chave
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v -k "health"
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v -k "database"

# Excluir testes
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v -k "not slow"
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v -m "not integration"
```

### Paralelização

```bash
# Usar todos os CPUs
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v -n auto

# Usar 4 workers
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v -n 4
```

### Modo Fail Fast

```bash
# Parar no primeiro erro
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v -x

# Parar após 3 falhas
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v --maxfail=3
```

### Verbosidade

```bash
# Modo verboso
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v

# Modo super verboso
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -vv

# Mostrar output do print
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ -v -s
```

---

## 🔧 Fixtures Disponíveis

As fixtures estão definidas em `conftest.py` e estão disponíveis para todos os testes.

### test_client

Cliente de teste FastAPI.

```python
def test_exemplo(self, test_client: TestClient):
    response = test_client.get("/health")
    assert response.status_code == 200
```

**Escopo:** function  
**Tipo:** TestClient  
**Auto-usa:** Não

### db_connection

Conexão direta ao PostgreSQL.

```python
def test_exemplo(self, db_connection):
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM market_data")
    count = cursor.fetchone()[0]
    assert count >= 0
```

**Escopo:** function  
**Tipo:** psycopg.Connection  
**Auto-usa:** Não  
**Cleanup:** Automático (yield)

### pgbouncer_connection

Conexão via PgBouncer.

```python
def test_exemplo(self, pgbouncer_connection):
    cursor = pgbouncer_connection.cursor()
    cursor.execute("SELECT version()")
    version = cursor.fetchone()[0]
    assert "PostgreSQL" in version
```

**Escopo:** function  
**Tipo:** psycopg.Connection  
**Auto-usa:** Não  
**Cleanup:** Automático (yield)

### sample_candle

Candle de exemplo para testes.

```python
def test_exemplo(self, sample_candle: dict, test_client: TestClient):
    response = test_client.post("/ingest", json=sample_candle)
    # ...
```

**Escopo:** function  
**Tipo:** dict  
**Conteúdo:**
```python
{
    "ts": "2025-01-15T14:30:00Z",
    "symbol": "EURUSD",
    "timeframe": "M1",
    "open": 1.0950,
    "high": 1.0955,
    "low": 1.0948,
    "close": 1.0952,
    "volume": 1250
}
```

### auth_headers

Headers de autenticação.

```python
def test_exemplo(self, auth_headers: dict, test_client: TestClient):
    response = test_client.post("/ingest", json=data, headers=auth_headers)
    # ...
```

**Escopo:** function  
**Tipo:** dict  
**Conteúdo:**
```python
{
    "X-API-Key": "mt5_trading_secure_key_2025_prod"
}
```

### cleanup_market_data

Limpa dados de teste após execução (autouse).

```python
# Não precisa declarar - é automático
def test_exemplo(self, db_connection):
    # Seus testes aqui
    # Dados serão limpos automaticamente após o teste
    pass
```

**Escopo:** function  
**Auto-usa:** Sim  
**Execução:** Após cada teste

### cleanup_signals

Limpa sinais de teste após execução (autouse).

**Escopo:** function  
**Auto-usa:** Sim  
**Execução:** Após cada teste

---

## ✍️ Criando Novos Testes

### Template Básico

```python
"""
Tests for [funcionalidade].
"""
import pytest
from fastapi.testclient import TestClient


class TestMinhaFuncionalidade:
    """Tests for [descrição]."""
    
    def test_comportamento_basico(self, test_client: TestClient):
        """Test basic behavior."""
        # Arrange
        data = {"key": "value"}
        
        # Act
        response = test_client.post("/endpoint", json=data)
        
        # Assert
        assert response.status_code == 200
        assert "expected_key" in response.json()
    
    def test_erro_esperado(self, test_client: TestClient):
        """Test error handling."""
        response = test_client.post("/endpoint", json={})
        assert response.status_code == 422
```

### Teste com Fixture

```python
def test_com_banco(self, db_connection, sample_candle: dict):
    """Test database operation."""
    cursor = db_connection.cursor()
    
    # Insert test data
    cursor.execute(
        """
        INSERT INTO market_data (ts, symbol, timeframe, open, high, low, close, volume)
        VALUES (%(ts)s, %(symbol)s, %(timeframe)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
        """,
        sample_candle
    )
    db_connection.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM market_data WHERE symbol = %(symbol)s", sample_candle)
    count = cursor.fetchone()[0]
    assert count == 1
```

### Teste Assíncrono

```python
import pytest

class TestAsync:
    """Tests for async endpoints."""
    
    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async operation."""
        result = await some_async_function()
        assert result is not None
```

### Teste Parametrizado

```python
@pytest.mark.parametrize("symbol,expected", [
    ("EURUSD", True),
    ("GBPUSD", True),
    ("INVALID", False),
])
def test_symbol_validation(self, test_client: TestClient, symbol: str, expected: bool):
    """Test symbol validation."""
    response = test_client.get(f"/data?symbol={symbol}")
    
    if expected:
        assert response.status_code == 200
    else:
        assert response.status_code == 422
```

---

## 🏷️ Markers e Categorias

### Markers Disponíveis

Configurados em `pytest.ini`:

```ini
[pytest]
markers =
    slow: marks tests as slow (>1s)
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    e2e: marks tests as end-to-end tests
    performance: marks tests as performance tests
```

### Como Usar

```python
import pytest

class TestPerformance:
    """Performance tests."""
    
    @pytest.mark.slow
    @pytest.mark.performance
    def test_bulk_insert(self, db_connection):
        """Test bulk insert performance."""
        # Teste demorado aqui
        pass
    
    @pytest.mark.integration
    def test_full_workflow(self, test_client: TestClient):
        """Test complete workflow."""
        # Teste de integração
        pass
```

### Executar por Marker

```bash
# Apenas testes lentos
pytest -m slow

# Apenas testes de integração
pytest -m integration

# Testes de unidade OU integração
pytest -m "unit or integration"

# Excluir testes lentos
pytest -m "not slow"
```

---

## 📊 Cobertura de Código

### Configuração

Em `pytest.ini`:

```ini
[pytest]
addopts = 
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=60
```

### Executar com Cobertura

```bash
# Completo
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ \
  --cov=app \
  --cov-report=html \
  --cov-report=term-missing

# Apenas para um módulo
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/test_api_endpoints.py \
  --cov=app.main \
  --cov-report=term-missing
```

### Ver Relatório

```bash
# Copiar para host
docker cp mt5_api:/app/htmlcov ./htmlcov

# Abrir no navegador
xdg-open htmlcov/index.html

# Ver no terminal
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/ \
  --cov=app \
  --cov-report=term-missing
```

### Análise de Cobertura

```bash
# Ver linhas não cobertas
pytest --cov=app --cov-report=term-missing

# Gerar XML para CI/CD
pytest --cov=app --cov-report=xml

# Falhar se cobertura < 60%
pytest --cov=app --cov-fail-under=60
```

---

## 🐛 Troubleshooting

### Import Errors

**Problema:**
```
ModuleNotFoundError: No module named 'app'
```

**Solução:**
```bash
# Definir PYTHONPATH
docker exec -e PYTHONPATH=/app mt5_api pytest /app/tests/
```

### Database Connection Failed

**Problema:**
```
psycopg.OperationalError: connection failed
```

**Solução:**
```bash
# Verificar se o banco está rodando
docker ps | grep mt5_db

# Verificar logs
docker logs mt5_db

# Inicializar schema
docker exec mt5_db psql -U admin -d mt5_db -f /docker-entrypoint-initdb.d/init.sql
```

### PgBouncer Connection Failed

**Problema:**
```
[Errno -3] Temporary failure in name resolution
```

**Solução:**
Já foi corrigido! PgBouncer tem network aliases configurados:
```yaml
# docker-compose.yml
pgbouncer:
  networks:
    default:
      aliases:
        - pgbouncer
        - mt5_pgbouncer
```

### Testes Lentos

**Problema:**
Testes demorando muito.

**Solução:**
```bash
# Usar paralelização
pytest -n auto

# Excluir testes lentos
pytest -m "not slow"

# Timeout para testes
pytest --timeout=30
```

### Fixtures Não Encontradas

**Problema:**
```
fixture 'test_client' not found
```

**Solução:**
- Verificar se `conftest.py` está no mesmo diretório
- Verificar se a fixture está definida
- Usar `pytest --fixtures` para listar fixtures disponíveis

### Cobertura Baixa

**Problema:**
Cobertura abaixo de 60%.

**Solução:**
1. Ver relatório: `pytest --cov=app --cov-report=term-missing`
2. Identificar linhas não cobertas
3. Criar testes para essas linhas
4. Ver [Relatório de Cobertura](RELATORIO_COBERTURA_TESTES.md) para detalhes

---

## 🎯 Best Practices

### 1. Testes Independentes

Cada teste deve ser independente e não depender de outros testes.

```python
# ❌ Ruim - dependência entre testes
def test_create_user(self):
    self.user_id = create_user()

def test_delete_user(self):
    delete_user(self.user_id)  # Depende do teste anterior

# ✅ Bom - testes independentes
def test_create_user(self):
    user_id = create_user()
    assert user_id is not None
    cleanup_user(user_id)

def test_delete_user(self):
    user_id = create_user()
    result = delete_user(user_id)
    assert result is True
```

### 2. Nomes Descritivos

Use nomes que descrevem o que está sendo testado.

```python
# ❌ Ruim
def test_1(self):
    pass

# ✅ Bom
def test_health_endpoint_returns_200_status_code(self):
    pass
```

### 3. Um Assert por Teste

Prefira um assert por teste para facilitar diagnóstico.

```python
# ❌ Ruim - múltiplos asserts
def test_response(self):
    response = get_data()
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "data" in response.json()

# ✅ Bom - separar em múltiplos testes
def test_response_status_code(self):
    response = get_data()
    assert response.status_code == 200

def test_response_status_field(self):
    response = get_data()
    assert response.json()["status"] == "ok"

def test_response_has_data_field(self):
    response = get_data()
    assert "data" in response.json()
```

### 4. Limpar Após Testes

Sempre limpar dados de teste.

```python
# ✅ Usar fixtures com yield
@pytest.fixture
def test_data(self, db_connection):
    # Setup
    data_id = insert_test_data()
    
    yield data_id
    
    # Cleanup
    delete_test_data(data_id)
```

### 5. Mockar Dependências Externas

Mockar APIs externas, ML models, etc.

```python
from unittest.mock import patch

def test_external_api(self):
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": "test"}
        
        result = call_external_api()
        assert result["data"] == "test"
```

### 6. Testar Edge Cases

Sempre testar casos extremos.

```python
def test_empty_input(self):
    response = process_data([])
    assert response == []

def test_null_input(self):
    response = process_data(None)
    assert response is None

def test_large_input(self):
    large_data = [{"item": i} for i in range(10000)]
    response = process_data(large_data)
    assert len(response) == 10000
```

### 7. Documentar Testes

Use docstrings para explicar o que está sendo testado.

```python
def test_candle_validation(self):
    """
    Test that the API validates candle data correctly.
    
    Should reject candles with:
    - Invalid timestamps
    - Negative prices
    - OHLC inconsistencies
    """
    # ...
```

---

## 📚 Recursos Adicionais

### Documentação

- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

### Arquivos Relacionados

- [Relatório de Cobertura](RELATORIO_COBERTURA_TESTES.md)
- [Análise Completa do Projeto](../architecture/ANALISE_COMPLETA_PROJETO.md)
- [pytest.ini](../../pytest.ini)
- [conftest.py](../../api/tests/conftest.py)

---

**Versão:** 1.0  
**Última Atualização:** 13/11/2025  
**Mantido por:** Equipe MT5 Process Core
