# ADR-005: Random Forest como Modelo ML Base

**Status**: ✅ Aceito
**Data**: 2025-02-10
**Autor**: Equipe ML
**Decisores**: Data Scientists, ML Engineers, Product Owner

## Contexto

O sistema precisa de modelos de Machine Learning para prever direção de mercado (classificação binária: BUY/SELL) baseado em features técnicas de trading.

Requisitos:

- **Performance preditiva**: Alta precision e recall em dados de mercado
- **Treinamento**: Tempo razoável com hardware limitado (CPU)
- **Interpretabilidade**: Entender quais features são importantes
- **Robustez**: Lidar com outliers e dados ruidosos
- **Manutenção**: Simplicidade para re-treinar e ajustar
- **Overfitting**: Evitar overfitting em dados temporais

## Decisão

Adotar **Random Forest Classifier** como modelo base para previsão de direção de mercado.

Random Forest oferece:

- Ensemble de árvores de decisão (robustez)
- Feature importance nativo
- Resistência a overfitting
- Não requer feature scaling
- Rápido treinamento em CPU
- Bom baseline antes de modelos complexos

## Alternativas Consideradas

### Alternativa 1: Regressão Logística

- **Prós**:
  - Muito rápido treinamento e inferência
  - Altamente interpretável (coeficientes lineares)
  - Baixo risco de overfitting
- **Contras**:
  - Assume relação linear entre features e target
  - Performance inferior em relações não-lineares
  - Dificuldade para capturar interações complexas

### Alternativa 2: XGBoost / LightGBM

- **Prós**:
  - State-of-the-art em tabular data
  - Performance superior em competições Kaggle
  - Otimizações para velocidade
- **Contras**:
  - Mais complexo para tuning (muitos hiperparâmetros)
  - Maior risco de overfitting (precisa regularização cuidadosa)
  - Menos interpretável que Random Forest
  - Curva de aprendizado maior

### Alternativa 3: Redes Neurais (LSTM/Transformer)

- **Prós**:
  - Captura dependências temporais longas
  - State-of-the-art em séries temporais complexas
  - Flexibilidade arquitetural
- **Contras**:
  - Requer GPU para treinamento eficiente
  - Muito mais dados necessários
  - Difícil interpretabilidade ("black box")
  - Overfitting fácil com poucos dados
  - Complexidade operacional (TensorFlow/PyTorch)

### Alternativa 4: SVM (Support Vector Machine)

- **Prós**:
  - Efetivo em espaços de alta dimensionalidade
  - Robusto a overfitting com kernel adequado
- **Contras**:
  - Muito lento para treinar com grandes datasets
  - Difícil interpretabilidade
  - Sensível à escala de features
  - Hiperparâmetros críticos (C, gamma)

## Consequências

### Positivas

- ✅ **Baseline Sólido**: Performance aceitável (60-70% accuracy) com pouco tuning
- ✅ **Feature Importance**: Identificar features mais relevantes facilmente
- ✅ **Robustez**: Resistente a outliers e ruído nos dados de mercado
- ✅ **Sem Scaling**: Não precisa normalizar features (economiza pipeline)
- ✅ **Treinamento CPU**: Treina em minutos sem necessidade de GPU
- ✅ **Overfitting Controlado**: Menos propenso que single decision tree
- ✅ **Simplicidade**: Fácil entender e explicar para stakeholders
- ✅ **Ecosystem**: scikit-learn bem documentado e maduro

### Negativas

- ❌ **Teto de Performance**: Unlikely alcançar 80%+ accuracy
- ❌ **Tamanho do Modelo**: Modelos grandes (100+ trees) ocupam espaço
- ❌ **Inferência**: Mais lento que Logistic Regression para prediction
- ❌ **Temporal Patterns**: Não captura dependências temporais explicitamente

### Riscos

- ⚠️ **Data Leakage**: Features baseadas em dados futuros
  - **Mitigação**: Validation rigoroso com time-series split
- ⚠️ **Market Regime Change**: Modelo pode degradar em mudanças de mercado
  - **Mitigação**: Re-treinar regularmente (daily), monitorar drift
- ⚠️ **Feature Engineering**: Performance depende de boas features
  - **Mitigação**: Exploração contínua de novas features técnicas

## Detalhes de Implementação

### Configuração do Modelo

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
import joblib

# Hiperparâmetros otimizados
model = RandomForestClassifier(
    n_estimators=100,        # Número de árvores
    max_depth=10,            # Profundidade máxima (evitar overfitting)
    min_samples_split=50,    # Mínimo amostras para split
    min_samples_leaf=20,     # Mínimo amostras por folha
    max_features='sqrt',     # Features por split (controle de correlação)
    random_state=42,         # Reprodutibilidade
    n_jobs=-1,               # Paralelizar treinamento
    class_weight='balanced'  # Lidar com desbalanceamento
)
```

### Features Utilizadas

```python
features = [
    # Price features
    "close", "open", "high", "low",

    # Volume
    "volume", "spread",

    # Technical indicators
    "rsi",              # Relative Strength Index
    "macd",             # MACD line
    "macd_signal",      # MACD signal
    "macd_hist",        # MACD histogram
    "atr",              # Average True Range
    "ma60",             # Moving Average 60

    # Lag features
    "ret_1",            # Return 1 period ago
    "ret_5",            # Return 5 periods ago
    "ret_10",           # Return 10 periods ago

    # Volatility
    "volatility_10",    # Rolling std dev 10 periods
]

# Target: direção do retorno futuro (5 períodos à frente)
# 1 = BUY (fwd_ret_5 > 0), 0 = SELL (fwd_ret_5 <= 0)
y = (df["fwd_ret_5"] > 0).astype(int)
```

### Treinamento com Time-Series Split

```python
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Time-series cross-validation (5 folds)
tscv = TimeSeriesSplit(n_splits=5)

scores = []
for train_idx, val_idx in tscv.split(X):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

    model.fit(X_train, y_train)
    y_pred = model.predict(X_val)

    scores.append({
        'accuracy': accuracy_score(y_val, y_pred),
        'precision': precision_score(y_val, y_pred),
        'recall': recall_score(y_val, y_pred),
        'f1': f1_score(y_val, y_pred)
    })

# Treinar modelo final com todos os dados
model.fit(X, y)
joblib.dump(model, "/models/rf_m1.pkl")
```

### Feature Importance

```python
import pandas as pd

# Extrair importâncias
importances = pd.DataFrame({
    'feature': features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print(importances.head(10))
# Output:
#     feature         importance
# 0   rsi             0.156
# 1   macd_hist       0.142
# 2   atr             0.098
# ...
```

### Monitoramento de Drift

```python
# Salvar métricas de treinamento
import json

metrics = {
    "model_name": "rf_m1",
    "version": "1.0.0",
    "trained_at": datetime.now().isoformat(),
    "accuracy": float(scores[-1]['accuracy']),
    "precision": float(scores[-1]['precision']),
    "recall": float(scores[-1]['recall']),
    "f1": float(scores[-1]['f1']),
    "n_samples": len(X),
    "n_features": len(features)
}

with open("/models/rf_m1_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)
```

### Estratégia de Re-treinamento

```bash
# Systemd timer para re-treinar diariamente às 04:00
# systemd/mt5-ml-train.timer

[Unit]
Description=Daily ML Model Training

[Timer]
OnCalendar=*-*-* 04:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

## Métricas de Sucesso

### Performance Atual (M1 timeframe)

```
Accuracy:  0.6234
Precision: 0.6589
Recall:    0.5891
F1 Score:  0.6220

Feature Importance Top 5:
1. RSI: 15.6%
2. MACD Histogram: 14.2%
3. ATR: 9.8%
4. MA60 Distance: 8.7%
5. Return Lag 1: 7.3%
```

### Thresholds de Alerta

```yaml
# Alertar se métricas caírem abaixo de:
accuracy_threshold: 0.55
precision_threshold: 0.60
recall_threshold: 0.50
```

## Próximos Passos

1. **Feature Engineering**: Testar features avançadas (Bollinger Bands, Ichimoku, order flow)
2. **Ensemble Stacking**: Combinar Random Forest com Logistic Regression
3. **Hyperparameter Tuning**: Grid search com RandomizedSearchCV
4. **Alternative Models**: Testar LightGBM se accuracy < 0.55
5. **Multi-timeframe**: Treinar modelos separados para M5, M15, H1

## Referências

- [Random Forests - Breiman (2001)](https://link.springer.com/article/10.1023/A:1010933404324)
- [scikit-learn Random Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)
- [Financial Time Series Forecasting with ML](https://arxiv.org/abs/1904.05315)
- [Feature Engineering for Trading](https://www.quantstart.com/articles/Feature-Engineering-for-Quantitative-Trading/)
- Notebook interno: `notebooks/rf_baseline_evaluation.ipynb`
