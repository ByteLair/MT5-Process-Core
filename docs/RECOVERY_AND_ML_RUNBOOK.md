## Resumo de recuperação, importação de dados e pipeline ML

Data do relatório: 2025-10-27

Este documento descreve as ações realizadas para restaurar o runtime do repositório, importar histórico EURUSD M1, preparar dataset para treino e executar um treino/avaliação mínima do modelo Informer-like.

## Objetivos principais
- Restaurar containers essenciais e API (garantir `API_KEY` para ingestão do EA).
- Importar histórico `EURUSD M1` fornecido em `HistoricalFIles/history_EURUSD_M1.jsonl` para a tabela `public.market_data`.
- Exportar os dados importados para CSV/Parquet e calcular scalers (mean/std).
- Construir dataset de janelas (sliding windows) pronto para treinamento.
- Treinar um modelo Transformer reduzido (SmallTransformer / Informer-like) em CPU e avaliar com splits variados.

## Ambiente e informações úteis
- Workspace: `/home/felipe/MT5-Process-Core-full`
- Virtualenv do projeto: `/home/felipe/MT5-Process-Core-full/.venv`
- Banco: TimescaleDB (container Docker, DB `mt5_trading`, user `trader`).
- API: FastAPI em `api/` com autenticação via header `X-API-KEY`. A chave usada: `mt5_trading_secure_key_2025_prod`.

## Passos realizados (ordem cronológica)

1. Reparos e configuração da API
   - Verificações de permissões/portas e reinício dos containers necessários.
   - Atualização de `.env` e `api/.env` para incluir `API_KEY=mt5_trading_secure_key_2025_prod` e `API_LOG_VERBOSE=true`.
   - Adição de middleware de logging de corpo de requisição em `api/app/main.py` (para depurar requisições de ingest do EA).

2. Banco de dados
   - Iniciou-se o container `db` (TimescaleDB) via `docker-compose`.
   - Para evitar conflitos com restores de extensão Timescale, optou-se por importar dados via COPY em vez de um dump/restore completo.

3. Importação do histórico EURUSD M1
   - Arquivo fonte: `HistoricalFIles/history_EURUSD_M1.jsonl` (fornecido pelo usuário).
   - Procedimento: conversão JSONL → CSV em stream Python, e import `COPY` para `public.market_data`.
   - Resultado: `COPY 99999` → 99.999 linhas inseridas.
   - Range temporal importado: primeiro ts = 2025-07-21T08:21:00+00 ; último ts = 2025-10-24T23:57:00+00.
   - Rodado: `VACUUM ANALYZE public.market_data;`

4. Exportação e transformação para ML
   - Exportou-se EURUSD M1 para `exports/eurusd_m1.csv` via psql `\copy`.
   - Converteu-se CSV → Parquet com Pandas/pyarrow: `exports/eurusd_m1.parquet` gerado.
   - Calculou-se scalers (mean/std) para colunas numéricas e salvou em `exports/eurusd_m1_scalers.json`.

5. Pipeline de dataset
   - Adicionados scripts:
     - `ml/build_windows_dataset.py` — constrói janelas deslizantes (seq_len, pred_len, step) normalizadas usando os scalers.
     - `ml/train_informer_small.py` — script de treino minimal (SmallTransformer) que salva checkpoint `ml/informer_small_ckpt.pth`.
   - Execução do builder:
     - Comandos usados (executados no venv):

```bash
/.venv/bin/python ml/build_windows_dataset.py \
  --parquet exports/eurusd_m1.parquet \
  --scalers exports/eurusd_m1_scalers.json \
  --out ml/dataset_eurusd.npz \
  --seq_len 480 --pred_len 60 --step 60
```

   - Resultado: `ml/dataset_eurusd.npz` criado com: X=(1658, 480, 5) e Y=(1658, 60).

6. Treino inicial
   - Instalou-se PyTorch no venv e foi executado o treino rápido de 5 épocas com `ml/train_informer_small.py`.
   - Métricas de treino (5 épocas):
     - Ep1: MAE 0.439623
     - Ep2: MAE 0.231216
     - Ep3: MAE 0.200443
     - Ep4: MAE 0.189242
     - Ep5: MAE 0.176819
   - Checkpoint salvo: `ml/informer_small_ckpt.pth`.

7. Avaliação com splits/épocas variados
   - Criado `ml/eval_informer_small.py` para treinar+avaliar com split configurável e salvar previsões.
   - Executados os testes pedidos (val_splits = 30%, 20%, 10% e epochs = 5, 10, 20) — 9 execuções no total.
   - Arquivos de saída de previsões:
     - `ml/eval_preds_5ep_30pct.npz`, `ml/eval_preds_10ep_30pct.npz`, `ml/eval_preds_20ep_30pct.npz`
     - `ml/eval_preds_5ep_20pct.npz`, `ml/eval_preds_10ep_20pct.npz`, `ml/eval_preds_20ep_20pct.npz`
     - `ml/eval_preds_5ep_10pct.npz`, `ml/eval_preds_10ep_10pct.npz`, `ml/eval_preds_20ep_10pct.npz`

   - Resultados de validação (MAE / RMSE):
     - val_split = 30% (497 exemplos)
       - 5 ep  — MAE 0.194096, RMSE 0.284351
       - 10 ep — MAE 0.165079, RMSE 0.220754
       - 20 ep — MAE 0.161923, RMSE 0.212279

     - val_split = 20% (332 exemplos)
       - 5 ep  — MAE 0.216921, RMSE 0.299308
       - 10 ep — MAE 0.160114, RMSE 0.207558
       - 20 ep — MAE 0.154226, RMSE 0.203215

     - val_split = 10% (166 exemplos)
       - 5 ep  — MAE 0.166319, RMSE 0.251223
       - 10 ep — MAE 0.154486, RMSE 0.203799
       - 20 ep — MAE 0.153452, RMSE 0.202197

   - Observação: o melhor MAE observado foi 0.153452 (val_split=10%, 20 ep). Splits menores tendem a mostrar métricas melhores por terem menos exemplos de validação — use val_split >=20% para métricas mais confiáveis.

## Arquivos criados/alterados importantes

- Modificados:
  - `api/.env`, `.env` — definições de `API_KEY` e `API_LOG_VERBOSE`.
  - `api/app/main.py` — middleware para logging de corpo de requisição (quando `API_LOG_VERBOSE=true`).

- Criados:
  - `exports/eurusd_m1.csv` — export CSV (99.999 linhas).
  - `exports/eurusd_m1.parquet` — Parquet do export.
  - `exports/eurusd_m1_scalers.json` — scalers (mean/std) usados no pré-processamento.
  - `ml/build_windows_dataset.py` — constrói janelas sliding-window.
  - `ml/train_informer_small.py` — treino minimal do SmallTransformer; salva `ml/informer_small_ckpt.pth`.
  - `ml/eval_informer_small.py` — novo script de treino+avaliação configurável.
  - `ml/dataset_eurusd.npz` — dataset final com X e Y.
  - `ml/informer_small_ckpt.pth` — checkpoint do primeiro treino.
  - `ml/eval_preds_*.npz` — arquivos com previsões e targets para cada experimento.

## Como reproduzir (comandos executados aqui)

Ative o venv do projeto e rode os scripts abaixo (exemplos):

```bash
# ativar venv (se aplicável)
source .venv/bin/activate

# converter CSV -> Parquet e calcular scalers (script usado interativamente)
python scripts/convert_csv_to_parquet_and_scalers.py \
  --in exports/eurusd_m1.csv --out exports/eurusd_m1.parquet --scalers exports/eurusd_m1_scalers.json

# construir dataset de janelas
python ml/build_windows_dataset.py \
  --parquet exports/eurusd_m1.parquet \
  --scalers exports/eurusd_m1_scalers.json \
  --out ml/dataset_eurusd.npz --seq_len 480 --pred_len 60 --step 60

# treinar modelo baseline (5 ep exemplo)
python ml/train_informer_small.py --data ml/dataset_eurusd.npz --epochs 5

# executar avaliação com split custom
python ml/eval_informer_small.py --data ml/dataset_eurusd.npz --val_split 0.2 --epochs 20
```

> Nota: alguns scripts auxiliares (ex.: conversão CSV→Parquet) foram executados ad-hoc no ambiente do venv; adapte o caminho caso queira reproduzir exatamente.

## Observações técnicas e recomendações

- Reprodutibilidade e splits temporais: o split usado nas avaliações foi randômico com seed fixa (42). Para séries temporais é preferível usar uma validação temporal (train até T, val após T) para medir real generalização temporal.

- Early stopping: implementar early stopping com base em validação evita treinar epochs demais e automatiza seleção de checkpoint.

- Export/serving: para deploy em CPU, recomendo exportar o modelo para ONNX e aplicar quantização dinâmica (ou usar PyTorch quantization) e testar latências no ambiente alvo.

- Pipeline incremental: planejar um pipeline que:
  1. coleta novas janelas diárias
  2. faz um fine-tune incremental (p.ex. 1–2 epochs) com replay de um buffer 
  3. valida em holdout temporal para evitar drift/catastrophic forgetting

## Próximos passos sugeridos (prioritizados)
1. Implementar avaliação temporal (time-based split) e re-rodar experimentos.
2. Adicionar early-stopping e salvar o melhor checkpoint por validação.
3. Exportar o melhor modelo para ONNX e aplicar quantização dinâmica, medir latência em CPU.
4. Automatizar pipeline de ingest → dataset → treino incremental via um script/cron ou containerized job.

## Contatos / logs
- Logs de execução e outputs estão no terminal histórico; arquivos de artefatos estão localizados em `ml/` e `exports/`.

Se quiser, eu:
- gero plots comparando previsões x reais para algumas janelas de validação,
- implemento early-stopping e re-treino o modelo final com checkpoint automático,
- ou exporto o melhor checkpoint para ONNX e faço quantização e teste de latência.

Escolha o próximo passo que quer que eu execute e eu prossigo.
