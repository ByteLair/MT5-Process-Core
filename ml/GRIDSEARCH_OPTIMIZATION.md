# Otimizações de Grid Search - Train Informer

## Problema Identificado

Grid search caindo para 3% de uso de CPU apesar de 28 cores disponíveis e 162 configurações para testar.

## Causa Raiz

Contenção de threads: cada worker do joblib estava criando múltiplos threads PyTorch, causando oversubscription e serialização involuntária.

## Correções Aplicadas

### 1. Configuração de Threads por Worker

```python
def evaluate_config(...):
    # Dentro de cada worker, limitar threads para evitar contenção
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
```

**Benefício**: Cada um dos 28 workers usa exatamente 1 thread, maximizando paralelismo real.

### 2. Logging Detalhado

Adicionado no início do script:

- Detecção de CPUs disponíveis
- Configuração de variáveis de ambiente (OMP/MKL/PYTORCH threads)
- Status do PyTorch (threads configurados)

**Benefício**: Visibilidade total da configuração para troubleshooting.

### 3. Verbose Mode no Joblib

```python
results = Parallel(n_jobs=n_jobs, prefer="processes", verbose=10)(...)
```

**Benefício**: Ver progresso em tempo real: "Done X out of Y | elapsed: Xs remaining: Ys"

### 4. Batch Size Ajustado

Reduzido de 64 para 32 em ambiente paralelo para evitar contenção de memória entre workers.

### 5. Relatório de Resultados

Após conclusão:

- Total de configs testadas
- Top 3 configurações por AUC-ROC
- Salvamento em JSON para análise posterior

## Ferramentas de Monitoramento

### Script de Monitor (`ml/monitor_gridsearch.sh`)

```bash
./ml/monitor_gridsearch.sh
```

Monitora em tempo real:

- % uso de CPU
- Memória RAM utilizada
- Número de workers Python ativos

### Teste de Paralelização (`ml/test_parallelization.py`)

```bash
python ml/test_parallelization.py
```

Valida que joblib + PyTorch conseguem usar múltiplos cores:

- ✅ **PASSOU**: 8 PIDs únicos, speedup de 1.5x

## Grid de Hiperparâmetros (162 configs)

```python
param_grid = {
    "seq_len": [32, 64, 128],        # 3 valores
    "d_model": [64, 128, 256],       # 3 valores
    "e_layers": [2, 3, 4],           # 3 valores
    "dropout": [0.1, 0.2, 0.3],      # 3 valores
    "lr": [1e-3, 5e-4],              # 2 valores
}
# Total: 3 × 3 × 3 × 3 × 2 = 162 configurações
```

## Uso Esperado de CPU

### Cenário Ideal

- **Início**: 28 workers ativos → ~95-99% CPU
- **Meio**: Alguns workers finalizando → 70-90% CPU
- **Final**: Poucos workers ativos → 20-40% CPU

### Se CPU cair abaixo de 50% no meio

Verificar:

1. `htop` → ver se processos `python` estão em estado `S` (sleeping) ou `R` (running)
2. Logs do joblib verbose → confirmar progresso
3. `iostat -x 5` → verificar se I/O está sendo gargalo

## Variáveis de Ambiente Importantes

No Docker Compose (`ml-trainer` e `ml-scheduler`):

```yaml
environment:
  OMP_NUM_THREADS: "28"          # OpenMP
  MKL_NUM_THREADS: "28"          # Intel MKL
  OPENBLAS_NUM_THREADS: "28"     # OpenBLAS
  NUMEXPR_NUM_THREADS: "28"      # NumExpr
  PYTORCH_NUM_THREADS: "28"      # PyTorch (main process)
  N_JOBS: "-1"                   # Joblib usa todos os cores
  BATCH_SIZE: "32"               # Batch por worker (menor = menos mem/contenção)
```

## Próximos Passos

1. **Rodar gridsearch completo** e monitorar CPU:

   ```bash
   # Terminal 1
   docker exec -it mt5_ml_trainer python ml/train_informer_gridsearch.py

   # Terminal 2
   docker exec -it mt5_ml_trainer ./ml/monitor_gridsearch.sh
   ```

2. **Se CPU ainda baixo**, investigar:
   - Bottleneck de I/O (loading de dados)
   - Contenção de memória (batch_size muito alto)
   - Dataset muito pequeno (treino rápido demais)

3. **Otimizações futuras**:
   - Converter CSV → Parquet para I/O 3-5x mais rápido
   - Cache de datasets pré-processados
   - DataLoader do PyTorch com `num_workers > 0`

## Performance Baseline

- **Test parallelization**: 1.5x speedup com 8 tarefas em 28 cores
- **Esperado no gridsearch**: 15-25x speedup (162 configs em paralelo vs sequencial)
- **Tempo estimado**: Se cada config leva ~3min sequencial, paralelo ~20-30min total

## Comandos Úteis

```bash
# Ver uso de CPU por core
mpstat -P ALL 1

# Ver processos Python mais pesados
ps aux | grep python | sort -k3 -r | head -10

# Uso de memória RAM
free -h

# Disco I/O
iostat -x 1
```
