#!/usr/bin/env python3
"""
⚔️ COMPARE ALL MODELS - BATTLE ROYALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Treina e compara TODOS os modelos disponíveis:
  1. Random Forest (baseline)
  2. XGBoost
  3. LightGBM
  4. CatBoost

Métricas comparadas:
  • Accuracy (Train / Val / Test)
  • Training time
  • Inference time
  • Memory usage
  • Stability (degradation Train→Test)

OBJETIVO: Escolher o MELHOR modelo para TRADING REAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import time
import logging
import psutil
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier, Pool

# ============================================================================
# SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/compare_models.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'forex_data'),
    'user': os.getenv('POSTGRES_USER', 'forex_user'),
    'password': os.getenv('POSTGRES_PASSWORD', 'forex_pass')
}

# ============================================================================
# MODEL CONFIGURATIONS
# ============================================================================

MODELS = {
    'Random Forest': {
        'model': RandomForestClassifier,
        'params': {
            'n_estimators': 200,
            'max_depth': 15,
            'min_samples_split': 50,
            'min_samples_leaf': 20,
            'class_weight': 'balanced',
            'random_state': 42,
            'n_jobs': -1,
            'verbose': 0
        },
        'supports_categorical': False
    },
    
    'XGBoost': {
        'model': XGBClassifier,
        'params': {
            'n_estimators': 300,
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'gamma': 0.1,
            'min_child_weight': 3,
            'scale_pos_weight': 1,
            'random_state': 42,
            'eval_metric': 'logloss',
            'early_stopping_rounds': 50,
            'verbose': 0
        },
        'supports_categorical': False
    },
    
    'LightGBM': {
        'model': LGBMClassifier,
        'params': {
            'n_estimators': 300,
            'max_depth': 8,
            'learning_rate': 0.05,
            'num_leaves': 31,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1,
            'min_child_samples': 20,
            'random_state': 42,
            'verbose': -1
        },
        'supports_categorical': False
    },
    
    'CatBoost': {
        'model': CatBoostClassifier,
        'params': {
            'iterations': 500,
            'learning_rate': 0.03,
            'depth': 6,
            'l2_leaf_reg': 5,
            'random_strength': 2,
            'bagging_temperature': 1.0,
            'subsample': 0.8,
            'rsm': 0.8,
            'od_type': 'Iter',
            'od_wait': 50,
            'task_type': 'CPU',
            'random_seed': 42,
            'verbose': False
        },
        'supports_categorical': True
    }
}

# ============================================================================
# DATA LOADING
# ============================================================================

def load_data():
    """Carrega dados do PostgreSQL."""
    logger.info("📥 Carregando dados...")
    
    query = """
    SELECT 
        ts,
        open, high, low, close, volume,
        rsi_14, macd, macd_signal, macd_hist,
        bb_upper, bb_middle, bb_lower,
        atr_14, adx_14,
        ema_50, ema_200,
        CASE 
            WHEN LEAD(close, 1) OVER (ORDER BY ts) > close THEN 1
            ELSE 0
        END as target
    FROM market_data
    WHERE 
        symbol = 'EURUSD' 
        AND timeframe = 'H1'
        AND ts >= '2015-01-01'
        AND ts <= '2025-11-30'
        AND rsi_14 IS NOT NULL
    ORDER BY ts
    """
    
    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    logger.info(f"✅ Carregados {len(df):,} candles")
    return df


def engineer_features(df):
    """Feature engineering."""
    df = df.copy()
    
    # Numeric features
    df['returns'] = df['close'].pct_change()
    df['returns_5'] = df['close'].pct_change(5)
    df['high_low_pct'] = (df['high'] - df['low']) / df['close']
    df['close_open_pct'] = (df['close'] - df['open']) / df['open']
    df['rsi_overbought'] = (df['rsi_14'] > 70).astype(int)
    df['rsi_oversold'] = (df['rsi_14'] < 30).astype(int)
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    df['ema_diff'] = df['ema_50'] - df['ema_200']
    df['price_above_ema50'] = (df['close'] > df['ema_50']).astype(int)
    df['price_above_ema200'] = (df['close'] > df['ema_200']).astype(int)
    df['volume_ma20'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma20']
    
    # Categorical features
    df['hour'] = df['ts'].dt.hour
    df['day_of_week'] = df['ts'].dt.dayofweek
    df['session'] = df['hour'].apply(
        lambda h: 'Asian' if 0 <= h < 8 else ('European' if 8 <= h < 16 else 'US')
    )
    df['trend'] = np.where(
        df['ema_50'] > df['ema_200'], 'Bullish',
        np.where(df['ema_50'] < df['ema_200'], 'Bearish', 'Ranging')
    )
    df['atr_ma20'] = df['atr_14'].rolling(20).mean()
    df['volatility_regime'] = np.where(
        df['atr_14'] > df['atr_ma20'] * 1.5, 'High',
        np.where(df['atr_14'] < df['atr_ma20'] * 0.5, 'Low', 'Normal')
    )
    
    df = df.dropna()
    return df


def split_data(df):
    """Split temporal."""
    train_mask = (df['ts'] >= '2015-01-01') & (df['ts'] <= '2023-12-31')
    val_mask = (df['ts'] >= '2024-01-01') & (df['ts'] <= '2024-09-30')
    test_mask = (df['ts'] >= '2024-10-01') & (df['ts'] <= '2025-11-30')
    
    return df[train_mask].copy(), df[val_mask].copy(), df[test_mask].copy()


def prepare_features(df, categorical_features, one_hot_encode=False):
    """Prepara features."""
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
    
    # One-hot encode categorical if needed
    if one_hot_encode:
        X = pd.get_dummies(X, columns=categorical_features)
    
    return X, y


# ============================================================================
# MODEL TRAINING & EVALUATION
# ============================================================================

def train_and_evaluate_model(name, model_config, X_train, y_train, X_val, y_val, X_test, y_test, categorical_features):
    """Treina e avalia um modelo."""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🔥 Training {name}")
    logger.info(f"{'='*60}")
    
    results = {'name': name}
    
    # Memory before
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    try:
        # Prepare data based on model support
        if model_config['supports_categorical']:
            X_train_prep, y_train_prep = X_train.copy(), y_train.copy()
            X_val_prep, y_val_prep = X_val.copy(), y_val.copy()
            X_test_prep, y_test_prep = X_test.copy(), y_test.copy()
            
            # CatBoost needs categorical indices
            if name == 'CatBoost':
                cat_indices = [i for i, col in enumerate(X_train.columns) if col in categorical_features]
                model_config['params']['cat_features'] = cat_indices
        else:
            # One-hot encode for sklearn/xgboost/lightgbm
            X_train_prep = pd.get_dummies(X_train, columns=categorical_features)
            X_val_prep = pd.get_dummies(X_val, columns=categorical_features)
            X_test_prep = pd.get_dummies(X_test, columns=categorical_features)
            
            # Align columns
            X_train_prep, X_val_prep = X_train_prep.align(X_val_prep, join='left', axis=1, fill_value=0)
            X_train_prep, X_test_prep = X_train_prep.align(X_test_prep, join='left', axis=1, fill_value=0)
            
            y_train_prep, y_val_prep, y_test_prep = y_train, y_val, y_test
        
        # Initialize model
        model = model_config['model'](**model_config['params'])
        
        # Train
        logger.info(f"⏱️  Training with {len(X_train_prep):,} samples...")
        train_start = time.time()
        
        if name in ['XGBoost', 'LightGBM']:
            model.fit(
                X_train_prep, y_train_prep,
                eval_set=[(X_val_prep, y_val_prep)],
                verbose=False
            )
        else:
            model.fit(X_train_prep, y_train_prep)
        
        train_time = time.time() - train_start
        results['train_time'] = train_time
        
        logger.info(f"✅ Training completed in {train_time:.1f}s ({train_time/60:.1f}min)")
        
        # Memory after
        mem_after = process.memory_info().rss / 1024 / 1024
        results['memory_mb'] = mem_after - mem_before
        
        # Inference time
        inference_start = time.time()
        _ = model.predict(X_test_prep)
        inference_time = time.time() - inference_start
        results['inference_time'] = inference_time
        results['inference_per_sample'] = (inference_time / len(X_test_prep)) * 1000  # ms
        
        # Evaluate on all sets
        for set_name, X, y in [
            ('train', X_train_prep, y_train_prep),
            ('val', X_val_prep, y_val_prep),
            ('test', X_test_prep, y_test_prep)
        ]:
            y_pred = model.predict(X)
            
            acc = accuracy_score(y, y_pred)
            prec = precision_score(y, y_pred, zero_division=0)
            rec = recall_score(y, y_pred, zero_division=0)
            f1 = f1_score(y, y_pred, zero_division=0)
            
            results[f'{set_name}_accuracy'] = acc
            results[f'{set_name}_precision'] = prec
            results[f'{set_name}_recall'] = rec
            results[f'{set_name}_f1'] = f1
            
            logger.info(f"   {set_name.upper():5s} | Acc: {acc:.4f} | Prec: {prec:.4f} | Rec: {rec:.4f} | F1: {f1:.4f}")
        
        # Stability (degradation)
        results['degradation'] = (results['train_accuracy'] - results['test_accuracy']) * 100
        
        logger.info(f"   Degradation (Train→Test): {results['degradation']:.2f}%")
        logger.info(f"   Memory used: {results['memory_mb']:.1f} MB")
        logger.info(f"   Inference: {results['inference_per_sample']:.3f} ms/sample")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error training {name}: {e}")
        return None


# ============================================================================
# MAIN
# ============================================================================

def main():
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║        ⚔️ MODEL COMPARISON - BATTLE ROYALE ⚔️            ║")
    logger.info("╚════════════════════════════════════════════════════════════╝")
    logger.info("")
    
    # Load data
    df = load_data()
    df = engineer_features(df)
    
    categorical_features = ['hour', 'day_of_week', 'session', 'trend', 'volatility_regime']
    
    # Split
    train_df, val_df, test_df = split_data(df)
    
    logger.info(f"📊 Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")
    
    # Prepare features (sem encoding, cada modelo fará o seu)
    X_train, y_train = prepare_features(train_df, categorical_features, one_hot_encode=False)
    X_val, y_val = prepare_features(val_df, categorical_features, one_hot_encode=False)
    X_test, y_test = prepare_features(test_df, categorical_features, one_hot_encode=False)
    
    # Train all models
    all_results = []
    
    for name, config in MODELS.items():
        result = train_and_evaluate_model(
            name, config,
            X_train, y_train,
            X_val, y_val,
            X_test, y_test,
            categorical_features
        )
        if result:
            all_results.append(result)
    
    # ========== COMPARISON TABLE ==========
    
    logger.info("\n\n")
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║                  🏆 FINAL COMPARISON                       ║")
    logger.info("╚════════════════════════════════════════════════════════════╝")
    logger.info("")
    
    # Create comparison DataFrame
    df_results = pd.DataFrame(all_results)
    
    # Print table
    logger.info("┌─────────────────────────────────────────────────────────────────────────────────┐")
    logger.info("│ MODEL         │ Train Acc │ Val Acc │ Test Acc │ Degrad │ Train Time │ Memory │")
    logger.info("├───────────────┼───────────┼─────────┼──────────┼────────┼────────────┼────────┤")
    
    for _, row in df_results.iterrows():
        logger.info(
            f"│ {row['name']:13s} │ "
            f"{row['train_accuracy']*100:6.2f}%   │ "
            f"{row['val_accuracy']*100:6.2f}% │ "
            f"{row['test_accuracy']*100:6.2f}%  │ "
            f"{row['degradation']:5.1f}% │ "
            f"{row['train_time']:7.1f}s   │ "
            f"{row['memory_mb']:5.0f}MB │"
        )
    
    logger.info("└─────────────────────────────────────────────────────────────────────────────────┘")
    
    # Find best
    best_test_acc = df_results.loc[df_results['test_accuracy'].idxmax()]
    best_stability = df_results.loc[df_results['degradation'].idxmin()]
    best_speed = df_results.loc[df_results['train_time'].idxmin()]
    
    logger.info("")
    logger.info("🏆 WINNERS:")
    logger.info(f"   Best Test Accuracy:  {best_test_acc['name']} ({best_test_acc['test_accuracy']*100:.2f}%)")
    logger.info(f"   Most Stable:         {best_stability['name']} ({best_stability['degradation']:.2f}% deg)")
    logger.info(f"   Fastest Training:    {best_speed['name']} ({best_speed['train_time']:.1f}s)")
    
    # Recommendation
    logger.info("")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("🎯 RECOMENDAÇÃO PARA TRADING:")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Score cada modelo
    df_results['score'] = (
        df_results['test_accuracy'] * 0.5 +  # 50% peso test accuracy
        (1 - df_results['degradation']/100) * 0.3 +  # 30% peso estabilidade
        (1 - df_results['train_time']/df_results['train_time'].max()) * 0.2  # 20% peso velocidade
    )
    
    winner = df_results.loc[df_results['score'].idxmax()]
    
    logger.info(f"   🥇 WINNER: {winner['name']}")
    logger.info(f"      • Test Accuracy: {winner['test_accuracy']*100:.2f}%")
    logger.info(f"      • Degradation: {winner['degradation']:.2f}%")
    logger.info(f"      • Training time: {winner['train_time']:.1f}s")
    logger.info(f"      • Overall score: {winner['score']:.4f}")
    logger.info("")
    
    if winner['test_accuracy'] >= 0.60:
        logger.info("   ✅ EXCELENTE! Accuracy >= 60% → READY FOR PRODUCTION")
    elif winner['test_accuracy'] >= 0.56:
        logger.info("   ⚠️  BOM. Accuracy 56-60% → Pode testar em paper trading")
    else:
        logger.info("   ❌ Accuracy < 56% → Precisa mais features ou dados")
    
    logger.info("")
    logger.info("   Next steps:")
    logger.info(f"   1. python scripts/ml/train_h1_{winner['name'].lower().replace(' ', '_')}.py")
    logger.info(f"   2. python scripts/ml/backtest_h1_{winner['name'].lower().replace(' ', '_')}.py")
    logger.info("   3. If ROI >= +2% → PRODUCTION! 🚀")
    logger.info("")
    
    # Save results
    df_results.to_csv('models/model_comparison.csv', index=False)
    logger.info("   💾 Results saved: models/model_comparison.csv")


if __name__ == '__main__':
    main()
