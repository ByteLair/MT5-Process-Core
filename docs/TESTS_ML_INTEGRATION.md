# Testes de ML e Integração

## 🎯 Visão Geral

Este documento descreve a infraestrutura de testes para os módulos de Machine Learning do projeto MT5 Trading, incluindo testes unitários, de integração e avançados para modelos Informer.

## 🔧 Configuração do Ambiente

### Estrutura de Testes

```
ml/
├── tests/
│   ├── conftest.py          # Configuração automática de sys.path
│   ├── test_ml.py           # Testes básicos (DB, treinamento, predição)
│   ├── test_ml_extended.py  # Testes de features e utilidades
│   └── test_ml_advanced.py  # Testes avançados (Informer, sequências, performance)
└── worker/
    └── train.py             # Módulo de treinamento refatorado
```

### Dependências Instaladas

Todas as dependências ML foram instaladas via `ml/requirements.txt`:

- **torch >= 2.0.0** (com suporte CPU)
- pandas, numpy, scikit-learn
- SQLAlchemy, psycopg, psycopg2-binary
- pytest, pytest-cov
- joblib, APScheduler

### Banco de Dados

O projeto oferece **duas opções de banco de dados** para testes:

#### Opção 1: Docker Compose (Recomendado)

```bash
# Porta 5432 já exposta no docker-compose.yml
docker-compose up -d db
export DATABASE_URL="postgresql+psycopg://trader:trader123@localhost:5432/mt5_trading"
```

#### Opção 2: Terraform (Isolado)

```bash
# Provisionado na porta 5433 para evitar conflitos
cd infra/terraform
terraform apply
export DATABASE_URL="postgresql+psycopg://trader:trader123@localhost:5433/mt5_trading"
```

### Variáveis de Ambiente

```bash
# Obrigatório para testes de integração
export DATABASE_URL="postgresql+psycopg://trader:trader123@localhost:5432/mt5_trading"

# Opcional: customizar diretório de logs (padrão: ./logs/ml/)
export LOG_DIR="./logs/ml/"

# Opcional: customizar diretório de modelos (padrão: ./models)
export MODELS_DIR="./models"
```

## 🚀 Como Rodar os Testes

### Setup Inicial (Uma Vez)

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Instalar dependências ML
pip install -r ml/requirements.txt

# Iniciar banco de dados
docker-compose up -d db
```

### Execução de Testes

#### Todos os Testes ML

```bash
# Não é mais necessário exportar PYTHONPATH!
# O conftest.py cuida disso automaticamente
pytest ml/tests --cov=ml --cov-report=term --cov-report=xml
```

#### Testes Específicos

```bash
# Apenas testes básicos
pytest ml/tests/test_ml.py -v

# Apenas testes estendidos
pytest ml/tests/test_ml_extended.py -v

# Apenas testes avançados (Informer)
pytest ml/tests/test_ml_advanced.py -v

# Excluir testes do Informer (mais rápido)
pytest ml/tests -k 'not informer' -v
```

#### Testes com Cobertura Detalhada

```bash
pytest ml/tests \
  --cov=ml \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml \
  -v
```

## 📊 O Que É Testado

### Testes Básicos (`test_ml.py`)

- ✅ Conexão com banco de dados (PostgreSQL/TimescaleDB)
- ✅ Treinamento de modelo RandomForest
- ✅ Salvamento e persistência de modelos (.pkl)
- ✅ Predição com modelo treinado

### Testes Estendidos (`test_ml_extended.py`)

- ✅ Cálculo de RSI (Relative Strength Index)
- ✅ Geração de features técnicas (`make_features`)
- ✅ Importação de módulos ML
- ✅ Validação de variáveis de ambiente
- ✅ Verificação de estrutura de diretórios
- ✅ Testes de avaliação de threshold (quando schema disponível)

### Testes Avançados (`test_ml_advanced.py`)

- ✅ Criação de sequências temporais (Informer)
- ✅ Feature engineering para modelos de séries temporais
- ✅ Casos extremos (RSI, preços constantes, NaN handling)
- ✅ Engenharia de features abrangente
- ✅ Propagação de NaN
- ✅ Reprodutibilidade de treinamento
- ✅ Persistência de modelos
- ✅ Performance de feature engineering (benchmark < 5s para 10k linhas)

## 📈 Cobertura Atual

### Estatísticas de Testes

- **Total de Testes**: 19 aprovados, 1 pulado
- **Cobertura ML**: ~22% (melhorado de ~6% inicial)
- **Tempo de Execução**: ~6-10 minutos (incluindo testes Informer)

### Arquivos Cobertos

```
ml/worker/train.py           # Engine DB e funções de treinamento
ml/prepare_dataset.py        # RSI, features técnicas
ml/train_informer_advanced.py # Sequências, features Informer
ml/eval_threshold.py         # Métricas e thresholds (skip se schema ausente)
```

### Relatórios Gerados

- `coverage.xml` - XML para integração CI/CD
- `htmlcov/` - Relatório HTML interativo
- Terminal - Resumo com linhas faltantes

## 🔄 Melhorias Implementadas

### 1. Refatoração do Módulo de Treinamento

**Arquivo**: `ml/worker/train.py`

**Problema Original**:

- Leitura do banco e treinamento executados no import
- Side effects causavam erros nos testes
- Engine criado mesmo quando não necessário

**Solução**:

```python
# Antes (execução no import)
df = pd.read_sql("SELECT * FROM trainset_m1", engine)
X = df[...].fillna(0)
m.fit(X, y)

# Depois (lazy execution)
def load_dataset(engine_):
    """Carrega dataset apenas quando chamado explicitamente."""
    return pd.read_sql("SELECT * FROM trainset_m1", engine_)

def train_and_save(df_local: pd.DataFrame) -> str:
    """Treina e salva modelo, retorna caminho."""
    # Lógica de treinamento

def main():
    df = load_dataset(engine)
    train_and_save(df)
```

**Benefícios**:

- ✅ Import rápido e sem side effects
- ✅ Engine disponível para testes (`from ml.worker.train import engine`)
- ✅ Funções testáveis isoladamente
- ✅ Controle explícito de quando treinar

### 2. Configuração Automática de Imports

**Arquivo**: `ml/tests/conftest.py`

**Problema Original**:

- Necessário `export PYTHONPATH=.` antes de cada teste
- Imports falhavam: `ModuleNotFoundError: No module named 'ml'`

**Solução**:

```python
"""
Configuração de testes do pacote ML.

Insere a raiz do repositório no sys.path para permitir imports absolutos
como `from ml.worker.train import engine` sem precisar exportar PYTHONPATH.
"""
import os
import sys

def _ensure_repo_root_on_path() -> None:
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(tests_dir, os.pardir, os.pardir))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

_ensure_repo_root_on_path()
```

**Benefícios**:

- ✅ Testes funcionam direto: `pytest ml/tests`
- ✅ Sem necessidade de configurar `PYTHONPATH`
- ✅ Compatível com IDEs e CI/CD
- ✅ Imports absolutos funcionam automaticamente

### 3. Instalação Completa de Dependências ML

**Ação**: Instalação de `ml/requirements.txt` com torch

```bash
pip install -r ml/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

**Pacotes Instalados**:

- torch >= 2.0.0 (versão CPU para CI/testes)
- Todas as dependências NVIDIA CUDA (para ambientes com GPU)
- triton (otimizações de kernel)

**Benefícios**:

- ✅ Testes avançados de Informer funcionam
- ✅ Modelo completo disponível para desenvolvimento
- ✅ CI pode rodar suite completa

## 🐛 Problemas Conhecidos e Soluções

### Teste Pulado: `test_eval_threshold_imports`

**Status**: Skip condicional quando schema não existe

**Razão**: Tabelas `features_h1` e `labels_h1` podem não existir em banco vazio

**Solução**:

```python
@pytest.mark.skipif(
    not _check_db_tables_exist(),
    reason="Schema features_h1/labels_h1 não existe no banco",
)
def test_eval_threshold_imports():
    from ml.eval_threshold import calculate_metrics
```

**Como Resolver**:

1. Popular banco com dados históricos
2. Executar `prepare_dataset.py` para criar features
3. Reexecutar testes: o skip será removido automaticamente

### Warnings de Deprecation

**Fonte**: SQLAlchemy 2.0 e numpy

**Status**: Não bloqueante, apenas informativos

**Ação**: Podem ser suprimidos com `--disable-warnings` ou corrigidos em sprint futuro

## 🎯 Próximos Passos

### Curto Prazo

1. **Lint e Type Check**
   - Executar `ruff check --fix ml` para corrigir imports
   - Executar `mypy ml` para validação de tipos
   - Integrar no CI para enforcement automático

2. **Atualização de Docs**
   - Remover instruções obsoletas de `PYTHONPATH`
   - Adicionar guia de troubleshooting
   - Documentar casos de uso de cada suite de testes

3. **Testes de API**
   - Criar `api/tests/test_integration.py`
   - Testar endpoints `/health`, `/predict`, `/signals`
   - Integrar com mesmo banco de testes
   - Adicionar ao CI

### Médio Prazo

1. **Expansão de Cobertura**
   - Meta: 60%+ de cobertura ML
   - Adicionar testes para `train_model.py`
   - Testar scheduler e workers
   - Validar pipeline completo end-to-end

2. **CI/CD Enhancement**
   - Badge de cobertura no README
   - Integração com Codecov/Coveralls
   - Testes paralelos para velocidade
   - Cache de dependências torch

3. **Performance Testing**
   - Benchmarks de treinamento
   - Testes de carga para API
   - Validação de memória/CPU usage

---

# 🌍 ENGLISH VERSION

## 🎯 Overview

This document describes the testing infrastructure for the MT5 Trading ML modules, including unit, integration, and advanced tests for Informer models.

## 🔧 Environment Setup

### Test Structure

```
ml/
├── tests/
│   ├── conftest.py          # Automatic sys.path configuration
│   ├── test_ml.py           # Basic tests (DB, training, prediction)
│   ├── test_ml_extended.py  # Feature and utility tests
│   └── test_ml_advanced.py  # Advanced tests (Informer, sequences, performance)
└── worker/
    └── train.py             # Refactored training module
```

### Installed Dependencies

All ML dependencies installed via `ml/requirements.txt`:

- **torch >= 2.0.0** (CPU support)
- pandas, numpy, scikit-learn
- SQLAlchemy, psycopg, psycopg2-binary
- pytest, pytest-cov
- joblib, APScheduler

### Database Options

The project offers **two database options** for testing:

#### Option 1: Docker Compose (Recommended)

```bash
# Port 5432 already exposed in docker-compose.yml
docker-compose up -d db
export DATABASE_URL="postgresql+psycopg://trader:trader123@localhost:5432/mt5_trading"
```

#### Option 2: Terraform (Isolated)

```bash
# Provisioned on port 5433 to avoid conflicts
cd infra/terraform
terraform apply
export DATABASE_URL="postgresql+psycopg://trader:trader123@localhost:5433/mt5_trading"
```

### Environment Variables

```bash
# Required for integration tests
export DATABASE_URL="postgresql+psycopg://trader:trader123@localhost:5432/mt5_trading"

# Optional: customize log directory (default: ./logs/ml/)
export LOG_DIR="./logs/ml/"

# Optional: customize models directory (default: ./models)
export MODELS_DIR="./models"
```

## 🚀 Running Tests

### Initial Setup (Once)

```bash
# Activate virtual environment
source .venv/bin/activate

# Install ML dependencies
pip install -r ml/requirements.txt

# Start database
docker-compose up -d db
```

### Test Execution

#### All ML Tests

```bash
# No need to export PYTHONPATH anymore!
# conftest.py handles this automatically
pytest ml/tests --cov=ml --cov-report=term --cov-report=xml
```

#### Specific Tests

```bash
# Basic tests only
pytest ml/tests/test_ml.py -v

# Extended tests only
pytest ml/tests/test_ml_extended.py -v

# Advanced tests only (Informer)
pytest ml/tests/test_ml_advanced.py -v

# Exclude Informer tests (faster)
pytest ml/tests -k 'not informer' -v
```

#### Tests with Detailed Coverage

```bash
pytest ml/tests \
  --cov=ml \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml \
  -v
```

## 📊 What Is Tested

### Basic Tests (`test_ml.py`)

- ✅ Database connection (PostgreSQL/TimescaleDB)
- ✅ RandomForest model training
- ✅ Model saving and persistence (.pkl)
- ✅ Trained model prediction

### Extended Tests (`test_ml_extended.py`)

- ✅ RSI (Relative Strength Index) calculation
- ✅ Technical features generation (`make_features`)
- ✅ ML module imports
- ✅ Environment variable validation
- ✅ Directory structure verification
- ✅ Threshold evaluation tests (when schema available)

### Advanced Tests (`test_ml_advanced.py`)

- ✅ Time series sequence creation (Informer)
- ✅ Feature engineering for time series models
- ✅ Edge cases (RSI, constant prices, NaN handling)
- ✅ Comprehensive feature engineering
- ✅ NaN propagation
- ✅ Training reproducibility
- ✅ Model persistence
- ✅ Feature engineering performance (benchmark < 5s for 10k rows)

## 📈 Current Coverage

### Test Statistics

- **Total Tests**: 19 passed, 1 skipped
- **ML Coverage**: ~22% (improved from ~6% initial)
- **Execution Time**: ~6-10 minutes (including Informer tests)

### Covered Files

```
ml/worker/train.py           # DB engine and training functions
ml/prepare_dataset.py        # RSI, technical features
ml/train_informer_advanced.py # Sequences, Informer features
ml/eval_threshold.py         # Metrics and thresholds (skip if schema absent)
```

### Generated Reports

- `coverage.xml` - XML for CI/CD integration
- `htmlcov/` - Interactive HTML report
- Terminal - Summary with missing lines

## 🔄 Implemented Improvements

### 1. Training Module Refactoring

**File**: `ml/worker/train.py`

**Original Problem**:

- Database read and training executed on import
- Side effects caused test errors
- Engine created even when not needed

**Solution**:

```python
# Before (execution on import)
df = pd.read_sql("SELECT * FROM trainset_m1", engine)
X = df[...].fillna(0)
m.fit(X, y)

# After (lazy execution)
def load_dataset(engine_):
    """Load dataset only when explicitly called."""
    return pd.read_sql("SELECT * FROM trainset_m1", engine_)

def train_and_save(df_local: pd.DataFrame) -> str:
    """Train and save model, return path."""
    # Training logic

def main():
    df = load_dataset(engine)
    train_and_save(df)
```

**Benefits**:

- ✅ Fast import without side effects
- ✅ Engine available for tests (`from ml.worker.train import engine`)
- ✅ Functions testable in isolation
- ✅ Explicit control of when to train

### 2. Automatic Import Configuration

**File**: `ml/tests/conftest.py`

**Original Problem**:

- Required `export PYTHONPATH=.` before each test
- Imports failed: `ModuleNotFoundError: No module named 'ml'`

**Solution**:

```python
"""
ML package test configuration.

Inserts repository root into sys.path to enable absolute imports
like `from ml.worker.train import engine` without needing to export PYTHONPATH.
"""
import os
import sys

def _ensure_repo_root_on_path() -> None:
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(tests_dir, os.pardir, os.pardir))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

_ensure_repo_root_on_path()
```

**Benefits**:

- ✅ Tests work directly: `pytest ml/tests`
- ✅ No need to configure `PYTHONPATH`
- ✅ Compatible with IDEs and CI/CD
- ✅ Absolute imports work automatically

### 3. Complete ML Dependencies Installation

**Action**: Installation of `ml/requirements.txt` with torch

```bash
pip install -r ml/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

**Installed Packages**:

- torch >= 2.0.0 (CPU version for CI/tests)
- All NVIDIA CUDA dependencies (for GPU environments)
- triton (kernel optimizations)

**Benefits**:

- ✅ Advanced Informer tests work
- ✅ Complete model available for development
- ✅ CI can run complete suite

## 🐛 Known Issues and Solutions

### Skipped Test: `test_eval_threshold_imports`

**Status**: Conditional skip when schema doesn't exist

**Reason**: Tables `features_h1` and `labels_h1` may not exist in empty database

**Solution**:

```python
@pytest.mark.skipif(
    not _check_db_tables_exist(),
    reason="Schema features_h1/labels_h1 doesn't exist in database",
)
def test_eval_threshold_imports():
    from ml.eval_threshold import calculate_metrics
```

**How to Fix**:

1. Populate database with historical data
2. Run `prepare_dataset.py` to create features
3. Re-run tests: skip will be automatically removed

### Deprecation Warnings

**Source**: SQLAlchemy 2.0 and numpy

**Status**: Non-blocking, informational only

**Action**: Can be suppressed with `--disable-warnings` or fixed in future sprint

## 🎯 Next Steps

### Short Term

1. **Lint and Type Check**
   - Run `ruff check --fix ml` to fix imports
   - Run `mypy ml` for type validation
   - Integrate into CI for automatic enforcement

2. **Documentation Updates**
   - Remove obsolete `PYTHONPATH` instructions
   - Add troubleshooting guide
   - Document use cases for each test suite

3. **API Tests**
   - Create `api/tests/test_integration.py`
   - Test endpoints `/health`, `/predict`, `/signals`
   - Integrate with same test database
   - Add to CI

### Medium Term

1. **Coverage Expansion**
   - Goal: 60%+ ML coverage
   - Add tests for `train_model.py`
   - Test scheduler and workers
   - Validate complete end-to-end pipeline

2. **CI/CD Enhancement**
   - Coverage badge in README
   - Integration with Codecov/Coveralls
   - Parallel tests for speed
   - Torch dependency caching

3. **Performance Testing**
   - Training benchmarks
   - API load tests
   - Memory/CPU usage validation
