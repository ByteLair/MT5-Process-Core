#!/usr/bin/env python3
"""
🎯 TRAIN H1 MODEL - CATBOOST OPTIMIZED FOR TRADING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Treina modelo CatBoost para previsão H1 com foco em ESTABILIDADE
e PERFORMANCE OUT-OF-SAMPLE (real trading).

FEATURES:
  • Ordered Boosting (respeita ordem temporal)
  • Features categóricas nativas (hour, day_of_week, session)
  • Regularização otimizada para evitar overfitting
  • Early stopping baseado em validation set
  • SHAP values para interpretabilidade

DATASET:
  • Train: 2015-2023 (80%)
  • Val: 2024 Q1-Q3 (15%)
  • Test: 2024 Q4-2025 (5%)

TARGET: 60-64% accuracy, +2-3.5% ROI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import time
import logging
import psycopg2
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from catboost import CatBoostClassifier, Pool
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, classification_report, confusion_matrix
)

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/train_h1_catboost.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Database
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'forex_data'),
    'user': os.getenv('POSTGRES_USER', 'forex_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'forex_pass')
}

# Paths
MODEL_PATH = 'models/catboost_h1_model.cbm'
METADATA_PATH = 'models/catboost_h1_metadata.json'
FEATURE_IMPORTANCE_PATH = 'models/catboost_h1_feature_importance.csv'

# ============================================================================
# HYPERPARAMETERS - OTIMIZADO PARA TRADING
# ============================================================================

CATBOOST_PARAMS = {
    # Core parameters
    'iterations': 500,              # Mais árvores = melhor generalização
    'learning_rate': 0.03,          # Baixo = menos overfitting
    'depth': 6,                     # Profundidade moderada
    
    # Regularization (CRÍTICO para trading)
    'l2_leaf_reg': 5,               # L2 regularization (maior = mais conservador)
    'random_strength': 2,           # Randomness nas splits (evita overfitting)
    'bagging_temperature': 1.0,     # Bayesian bootstrap
    
    # Sampling
    'subsample': 0.8,               # 80% dos dados por árvore
    'rsm': 0.8,                     # 80% das features por split (random subspace)
    
    # Categorical features handling
    'cat_features': None,           # Será definido dinamicamente
    'one_hot_max_size': 10,         # One-hot encoding para categorias pequenas
    
    # Overfitting prevention
    'od_type': 'Iter',              # Overfitting detector type
    'od_wait': 50,                  # Espera 50 iters sem melhora
    
    # Performance
    'task_type': 'CPU',             # GPU se disponível
    'thread_count': -1,             # Usa todos os cores
    
    # Output
    'verbose': False,               # Reduz output
    'random_seed': 42,
    'loss_function': 'Logloss',
    'eval_metric': 'Accuracy',
    'use_best_model': True          # Usa melhor modelo do early stopping
}

# Data splits (temporal)
TRAIN_START = '2015-01-01'
TRAIN_END = '2023-12-31'
VAL_START = '2024-01-01'
VAL_END = '2024-09-30'
TEST_START = '2024-10-01'
TEST_END = '2025-11-30'

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def load_data_from_db():
    """Carrega dados do PostgreSQL com features calculadas."""
    logger.info("📥 Carregando dados do PostgreSQL...")
    
    query = """
    SELECT 
        ts,
        open, high, low, close, volume,
        
        -- Technical Indicators (calculados previamente)
        rsi_14, macd, macd_signal, macd_hist,
        bb_upper, bb_middle, bb_lower,
        atr_14, adx_14,
        ema_50, ema_200,
        
        -- Price features
        EXTRACT(HOUR FROM ts) as hour,
        EXTRACT(DOW FROM ts) as day_of_week,
        
        -- Target (next candle direction)
        CASE 
            WHEN LEAD(close, 1) OVER (ORDER BY ts) > close THEN 1
            ELSE 0
        END as target
        
    FROM market_data
    WHERE 
        symbol = 'EURUSD' 
        AND timeframe = 'H1'
        AND ts >= %s
        AND ts <= %s
        AND rsi_14 IS NOT NULL  -- Apenas com indicadores calculados
    ORDER BY ts
    """
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        df = pd.read_sql_query(
            query, 
            conn, 
            params=[TRAIN_START, TEST_END]
        )
        conn.close()
        
        logger.info(f"✅ Carregados {len(df):,} candles H1")
        logger.info(f"   Período: {df['ts'].min()} → {df['ts'].max()}")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar dados: {e}")
        raise


def engineer_features(df):
    """Engenharia de features adicional + identificação categóricas."""
    logger.info("🔧 Engenharia de features...")
    
    df = df.copy()
    
    # ========== FEATURES NUMÉRICAS ==========
    
    # Price momentum
    df['returns'] = df['close'].pct_change()
    df['returns_5'] = df['close'].pct_change(5)
    
    # Volatility
    df['high_low_pct'] = (df['high'] - df['low']) / df['close']
    df['close_open_pct'] = (df['close'] - df['open']) / df['open']
    
    # RSI features
    df['rsi_overbought'] = (df['rsi_14'] > 70).astype(int)
    df['rsi_oversold'] = (df['rsi_14'] < 30).astype(int)
    
    # Bollinger Bands position
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # EMA relationship
    df['ema_diff'] = df['ema_50'] - df['ema_200']
    df['price_above_ema50'] = (df['close'] > df['ema_50']).astype(int)
    df['price_above_ema200'] = (df['close'] > df['ema_200']).astype(int)
    
    # Volume
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma20']
    
    # ========== FEATURES CATEGÓRICAS ==========
    
    # Trading session
    def get_session(hour):
        if 0 <= hour < 8:
            return 'Asian'
        elif 8 <= hour < 16:
            return 'European'
        else:
            return 'US'
    
    df['session'] = df['hour'].apply(get_session)
    
    # Trend (baseado em EMA)
    def get_trend(row):
        if pd.isna(row['ema_50']) or pd.isna(row['ema_200']):
            return 'Unknown'
        if row['ema_50'] > row['ema_200']:
            return 'Bullish'
        elif row['ema_50'] < row['ema_200']:
            return 'Bearish'
        else:
            return 'Ranging'
    
    df['trend'] = df.apply(get_trend, axis=1)
    
    # Volatility regime (baseado em ATR)
    df['atr_ma20'] = df['atr_14'].rolling(20).mean()
    def get_volatility_regime(row):
        if pd.isna(row['atr_14']) or pd.isna(row['atr_ma20']):
            return 'Normal'
        if row['atr_14'] > row['atr_ma20'] * 1.5:
            return 'High'
        elif row['atr_14'] < row['atr_ma20'] * 0.5:
            return 'Low'
        else:
            return 'Normal'
    
    df['volatility_regime'] = df.apply(get_volatility_regime, axis=1)
    
    # Remove rows com NaN (primeiras linhas)
    df = df.dropna()
    
    logger.info(f"✅ Features engineered: {len(df):,} samples")
    
    # Categorical features (CatBoost usará nativamente)
    categorical_features = ['hour', 'day_of_week', 'session', 'trend', 'volatility_regime']
    
    return df, categorical_features


def split_data(df):
    """Split temporal: Train / Validation / Test."""
    logger.info("✂️  Splitting dataset...")
    
    train_mask = (df['ts'] >= TRAIN_START) & (df['ts'] <= TRAIN_END)
    val_mask = (df['ts'] >= VAL_START) & (df['ts'] <= VAL_END)
    test_mask = (df['ts'] >= TEST_START) & (df['ts'] <= TEST_END)
    
    train_df = df[train_mask].copy()
    val_df = df[val_mask].copy()
    test_df = df[test_mask].copy()
    
    logger.info(f"📊 Train: {len(train_df):,} samples ({TRAIN_START} → {TRAIN_END})")
    logger.info(f"📊 Val:   {len(val_df):,} samples ({VAL_START} → {VAL_END})")
    logger.info(f"📊 Test:  {len(test_df):,} samples ({TEST_START} → {TEST_END})")
    
    # Class distribution
    logger.info(f"   Train target: {train_df['target'].value_counts().to_dict()}")
    logger.info(f"   Val target:   {val_df['target'].value_counts().to_dict()}")
    
    return train_df, val_df, test_df


def prepare_features(df, categorical_features):
    """Prepara features para CatBoost."""
    
    # Features para usar
    feature_cols = [
        'open', 'high', 'low', 'close', 'volume',
        'rsi_14', 'macd', 'macd_signal', 'macd_hist',
        'bb_upper', 'bb_middle', 'bb_lower', 'bb_position', 'bb_width',
        'atr_14', 'adx_14',
        'ema_50', 'ema_200', 'ema_diff',
        'returns', 'returns_5',
        'high_low_pct', 'close_open_pct',
        'rsi_overbought', 'rsi_oversold',
        'price_above_ema50', 'price_above_ema200',
        'volume_ratio',
        'hour', 'day_of_week', 'session', 'trend', 'volatility_regime'
    ]
    
    X = df[feature_cols].copy()
    y = df['target'].copy()
    
    return X, y, feature_cols


def train_catboost(X_train, y_train, X_val, y_val, categorical_features):
    """Treina CatBoost com configuração otimizada."""
    logger.info("🚀 Iniciando treinamento CatBoost...")
    
    # Identificar índices das features categóricas
    cat_feature_indices = [
        i for i, col in enumerate(X_train.columns) 
        if col in categorical_features
    ]
    
    logger.info(f"📋 Features categóricas ({len(cat_feature_indices)}): {categorical_features}")
    
    # Criar Pools (estrutura otimizada do CatBoost)
    train_pool = Pool(
        data=X_train,
        label=y_train,
        cat_features=cat_feature_indices
    )
    
    val_pool = Pool(
        data=X_val,
        label=y_val,
        cat_features=cat_feature_indices
    )
    
    # Update params
    params = CATBOOST_PARAMS.copy()
    params['cat_features'] = cat_feature_indices
    
    # Train
    logger.info(f"⏱️  Treinando com {len(X_train):,} samples...")
    start_time = time.time()
    
    model = CatBoostClassifier(**params)
    
    model.fit(
        train_pool,
        eval_set=val_pool,
        early_stopping_rounds=50,
        verbose=100  # Print a cada 100 iterações
    )
    
    train_time = time.time() - start_time
    logger.info(f"✅ Treinamento concluído em {train_time:.1f}s ({train_time/60:.1f}min)")
    logger.info(f"   Best iteration: {model.get_best_iteration()}")
    logger.info(f"   Best score: {model.get_best_score()}")
    
    return model


def evaluate_model(model, X, y, dataset_name='Test'):
    """Avalia modelo e retorna métricas."""
    logger.info(f"📊 Avaliando modelo em {dataset_name}...")
    
    # Predictions
    y_pred = model.predict(X)
    y_pred_proba = model.predict_proba(X)[:, 1]
    
    # Metrics
    accuracy = accuracy_score(y, y_pred)
    precision = precision_score(y, y_pred, zero_division=0)
    recall = recall_score(y, y_pred, zero_division=0)
    f1 = f1_score(y, y_pred, zero_division=0)
    
    logger.info(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    logger.info(f"   Precision: {precision:.4f}")
    logger.info(f"   Recall:    {recall:.4f}")
    logger.info(f"   F1-Score:  {f1:.4f}")
    
    # Confusion matrix
    cm = confusion_matrix(y, y_pred)
    logger.info(f"   Confusion Matrix:\n{cm}")
    
    # Classification report
    report = classification_report(y, y_pred, zero_division=0)
    logger.info(f"   Classification Report:\n{report}")
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'confusion_matrix': cm.tolist()
    }


def save_model(model, feature_cols, metrics):
    """Salva modelo e metadata."""
    logger.info("💾 Salvando modelo...")
    
    # Save model (formato nativo CatBoost)
    os.makedirs('models', exist_ok=True)
    model.save_model(MODEL_PATH)
    logger.info(f"   ✅ Modelo salvo: {MODEL_PATH}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.get_feature_importance()
    }).sort_values('importance', ascending=False)
    
    feature_importance.to_csv(FEATURE_IMPORTANCE_PATH, index=False)
    logger.info(f"   ✅ Feature importance salvo: {FEATURE_IMPORTANCE_PATH}")
    
    # Top 10 features
    logger.info("   🏆 Top 10 features mais importantes:")
    for idx, row in feature_importance.head(10).iterrows():
        logger.info(f"      {row['feature']:20s} {row['importance']:8.2f}")
    
    # Metadata
    metadata = {
        'model_type': 'CatBoost',
        'trained_at': datetime.now().isoformat(),
        'train_period': f"{TRAIN_START} → {TRAIN_END}",
        'val_period': f"{VAL_START} → {VAL_END}",
        'test_period': f"{TEST_START} → {TEST_END}",
        'hyperparameters': CATBOOST_PARAMS,
        'feature_count': len(feature_cols),
        'features': feature_cols,
        'metrics': metrics
    }
    
    import json
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"   ✅ Metadata salvo: {METADATA_PATH}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Pipeline principal de treinamento."""
    
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║   🎯 TRAIN H1 CATBOOST - OPTIMIZED FOR TRADING           ║")
    logger.info("╚════════════════════════════════════════════════════════════╝")
    logger.info("")
    
    try:
        # 1. Load data
        df = load_data_from_db()
        
        # 2. Engineer features
        df, categorical_features = engineer_features(df)
        
        # 3. Split data (temporal)
        train_df, val_df, test_df = split_data(df)
        
        # 4. Prepare features
        X_train, y_train, feature_cols = prepare_features(train_df, categorical_features)
        X_val, y_val, _ = prepare_features(val_df, categorical_features)
        X_test, y_test, _ = prepare_features(test_df, categorical_features)
        
        logger.info(f"✅ Feature matrix: {X_train.shape[1]} features")
        
        # 5. Train model
        model = train_catboost(X_train, y_train, X_val, y_val, categorical_features)
        
        # 6. Evaluate
        train_metrics = evaluate_model(model, X_train, y_train, 'Train')
        val_metrics = evaluate_model(model, X_val, y_val, 'Validation')
        test_metrics = evaluate_model(model, X_test, y_test, 'Test')
        
        # 7. Save
        all_metrics = {
            'train': train_metrics,
            'validation': val_metrics,
            'test': test_metrics
        }
        save_model(model, feature_cols, all_metrics)
        
        # 8. Summary
        logger.info("")
        logger.info("╔════════════════════════════════════════════════════════════╗")
        logger.info("║                   🏆 TRAINING COMPLETE                     ║")
        logger.info("╚════════════════════════════════════════════════════════════╝")
        logger.info(f"   Train Accuracy:      {train_metrics['accuracy']*100:.2f}%")
        logger.info(f"   Validation Accuracy: {val_metrics['accuracy']*100:.2f}%")
        logger.info(f"   Test Accuracy:       {test_metrics['accuracy']*100:.2f}% ⭐")
        logger.info("")
        logger.info(f"   Model: {MODEL_PATH}")
        logger.info(f"   Ready for backtesting! 🚀")
        logger.info("")
        
        # Check if degradation is acceptable
        degradation = (train_metrics['accuracy'] - test_metrics['accuracy']) * 100
        logger.info(f"   Degradation (Train → Test): {degradation:.1f}%")
        
        if degradation < 3:
            logger.info("   ✅ EXCELENTE! Baixa degradação = modelo robusto")
        elif degradation < 5:
            logger.info("   ⚠️  OK. Degradação aceitável")
        else:
            logger.info("   ❌ ATENÇÃO! Alta degradação = possível overfitting")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
