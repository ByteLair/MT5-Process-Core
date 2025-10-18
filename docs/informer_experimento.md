# Experimento Informer - Previsão de Trades Positivos

## Objetivo
Prever operações positivas (target_ret_1 > 0) em séries temporais de candles, maximizando precisão e recall, com pipeline flexível e otimizado para CPU.

## Pipeline
- **Feature engineering:** MACD, Bollinger Bands, volatilidade, lags, hora, dia da semana
- **Balanceamento:** Oversampling dos positivos
- **Data augmentation:** Bootstrapping dos dados de treino
- **Modelo:** Informer-like (TransformerEncoder)
- **Hiperparâmetros:** seq_len, d_model, d_ff, e_layers, batch_size, epochs, lr, dropout
- **Validação:** Early stopping, threshold tuning

## Resultados recentes

### Parâmetros usados
```
seq_len: 64
d_model: 128
d_ff: 256
e_layers: 3
batch_size: 64
epochs: 15
dropout: 0.2
lr: 0.001
oversample: True
augment: True
```

### Métricas
- **Threshold 0.5:**
  - Precision: 49.5%
  - Recall: 100%
  - AUC-ROC: 0.487
  - Positivos previstos: 100%
- **Threshold otimizado (0.52):**
  - Precision: 49.0%
  - Recall: 50.5%
  - Positivos previstos: 51.1%

## Arquivos gerados
- `ml/models/informer_classifier_advanced.pt` — modelo treinado
- `ml/models/informer_normalization_advanced.json` — normalização das features
- `ml/models/informer_report_advanced.json` — relatório completo de métricas e configurações

## Próximos passos
1. **Aprimorar hiperparâmetros:**
   - Testar seq_len maior (128, 256)
   - Aumentar d_model, d_ff, e_layers
   - Ajustar dropout, lr, batch_size
   - Testar epochs maiores
2. **Aprimorar arquitetura:**
   - Adicionar camadas (MLP após pooling, ativação GELU, regularização extra)
   - Testar ativação diferente (ReLU, GELU)
   - Experimentar pooling alternativo (max, attention)
3. **Testar mais features:**
   - Novos indicadores técnicos
   - Features de contexto macro
4. **Comparar com outros modelos:**
   - XGBoost, LightGBM, LSTM, GRU, CNN1D
5. **Automatizar grid search:**
   - Script para rodar múltiplas combinações e salvar os melhores resultados

## Observações
- O modelo ainda não atingiu precisão de 58%.
- O recall aumentou, mas a separação entre classes está limitada (AUC < 0.5).
- Mais dados e features podem ajudar.
- Documentação e scripts prontos para experimentação rápida.

---

*Relatório gerado automaticamente em 18/10/2025.*
