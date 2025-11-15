#!/usr/bin/env python3
"""
Treinar modelo Random Forest otimizado para H1
Strategy: Swing trading conservador com alta seletividade
"""
import os
import sys
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import json

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'mt5_trading'),
    'user': os.getenv('DB_USER', 'trader'),
    'password': os.getenv('DB_PASSWORD', 'trader123')
}

# Model configuration - CONSERVADOR
TARGET_HOURS_AHEAD = 4  # Predizer se preço sobe em próximas 4 horas
TRAIN_END_DATE = '2025-09-30'  # Treino: Jan 2024 - Set 2025
TEST_START_DATE = '2025-10-01'  # Teste: Out 2025 - Nov 2025

def create_features(df):
    """Create features for H1 model"""
    print("  🔧 Criando features...")
    
    # Price-based features
    df['returns'] = df['close'].pct_change()
    df['high_low_range'] = (df['high'] - df['low']) / df['close']
    df['close_open_range'] = (df['close'] - df['open']) / df['open']
    
    # Price relative to Bollinger Bands
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # MACD features
    df['macd_trend'] = (df['macd'] > df['macd_signal']).astype(int)
    df['macd_momentum'] = df['macd'] - df['macd_signal']
    
    # RSI zones
    df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
    df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
    df['rsi_neutral'] = ((df['rsi'] >= 40) & (df['rsi'] <= 60)).astype(int)
    
    # ATR normalized
    df['atr_normalized'] = df['atr'] / df['close']
    
    # Time features (important for H1)
    df['hour'] = pd.to_datetime(df['ts']).dt.hour
    df['day_of_week'] = pd.to_datetime(df['ts']).dt.dayofweek
    df['is_london_session'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)
    df['is_ny_session'] = ((df['hour'] >= 13) & (df['hour'] < 21)).astype(int)
    df['is_overlap'] = ((df['hour'] >= 13) & (df['hour'] < 16)).astype(int)
    
    # Momentum indicators
    df['price_above_bb_mid'] = (df['close'] > df['bb_middle']).astype(int)
    df['macd_above_zero'] = (df['macd'] > 0).astype(int)
    
    # Rolling statistics (H1 specific)
    df['returns_roll_mean_5'] = df['returns'].rolling(5).mean()
    df['returns_roll_std_5'] = df['returns'].rolling(5).std()
    df['volume_roll_mean_5'] = df['volume'].rolling(5).mean()
    
    return df

def create_target(df, hours_ahead=4):
    """Create target: price goes up in next N hours"""
    print(f"  🎯 Criando target (próximas {hours_ahead} horas)...")
    
    # Calculate future return
    df['future_close'] = df['close'].shift(-hours_ahead)
    df['future_return'] = (df['future_close'] - df['close']) / df['close']
    
    # Binary target: 1 if price goes up, 0 if down
    # Use minimum threshold to filter noise
    MIN_MOVE = 0.0002  # 2 pips minimum move
    df['target'] = (df['future_return'] > MIN_MOVE).astype(int)
    
    # Remove last rows (no future data)
    df = df[:-hours_ahead]
    
    return df

def main():
    print("\n" + "="*70)
    print("🤖 TREINAMENTO MODELO H1 - CONSERVADOR")
    print("="*70 + "\n")
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Load H1 data with indicators
        print("📊 Carregando dados H1 com indicadores...")
        query = """
            SELECT ts, open, high, low, close, volume,
                   rsi, macd, macd_signal, macd_hist,
                   bb_upper, bb_middle, bb_lower, atr
            FROM market_data
            WHERE symbol = 'EURUSD'
            AND timeframe = 'H1'
            AND rsi IS NOT NULL
            ORDER BY ts ASC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        print(f"✅ {len(df):,} candles H1 carregados\n")
        
        if len(df) < 1000:
            print("❌ Dados insuficientes para treino!")
            return
        
        # Create features and target
        print("🔧 Preparando dados...")
        df = create_features(df)
        df = create_target(df, hours_ahead=TARGET_HOURS_AHEAD)
        
        # Remove NaN rows
        df = df.dropna()
        print(f"✅ {len(df):,} candles após feature engineering\n")
        
        # Split train/test by date
        print("📅 Divisão temporal dos dados:")
        train_df = df[df['ts'] < TRAIN_END_DATE]
        test_df = df[df['ts'] >= TEST_START_DATE]
        
        print(f"  • Treino: {train_df['ts'].min()} até {train_df['ts'].max()}")
        print(f"  • Treino candles: {len(train_df):,}")
        print(f"  • Teste: {test_df['ts'].min()} até {test_df['ts'].max()}")
        print(f"  • Teste candles: {len(test_df):,}\n")
        
        # Select features
        feature_cols = [
            'returns', 'high_low_range', 'close_open_range',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'bb_position', 'bb_width', 'atr_normalized',
            'macd_trend', 'macd_momentum',
            'rsi_oversold', 'rsi_overbought', 'rsi_neutral',
            'hour', 'day_of_week',
            'is_london_session', 'is_ny_session', 'is_overlap',
            'price_above_bb_mid', 'macd_above_zero',
            'returns_roll_mean_5', 'returns_roll_std_5', 'volume_roll_mean_5'
        ]
        
        X_train = train_df[feature_cols]
        y_train = train_df['target']
        X_test = test_df[feature_cols]
        y_test = test_df['target']
        
        print("📊 Distribuição das classes:")
        print(f"  • Treino - UP: {y_train.sum():,} ({100*y_train.mean():.1f}%)")
        print(f"  • Treino - DOWN: {len(y_train)-y_train.sum():,} ({100*(1-y_train.mean()):.1f}%)")
        print(f"  • Teste - UP: {y_test.sum():,} ({100*y_test.mean():.1f}%)")
        print(f"  • Teste - DOWN: {len(y_test)-y_test.sum():,} ({100*(1-y_test.mean()):.1f}%)\n")
        
        # Train Random Forest (conservador)
        print("🌲 Treinando Random Forest...")
        print("  Parâmetros:")
        print("    • n_estimators: 300 (mais árvores = mais robusto)")
        print("    • max_depth: 15 (evita overfitting)")
        print("    • min_samples_split: 20 (conservador)")
        print("    • min_samples_leaf: 10 (conservador)")
        print("    • class_weight: balanced (lidar com desbalanceamento)\n")
        
        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=15,
            min_samples_split=20,
            min_samples_leaf=10,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1,
            verbose=1
        )
        
        model.fit(X_train, y_train)
        print("\n✅ Modelo treinado!\n")
        
        # Evaluate on test set
        print("📊 AVALIAÇÃO NO CONJUNTO DE TESTE (OUT-OF-SAMPLE):\n")
        
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Classification report
        print("📋 Classification Report:")
        print(classification_report(y_test, y_pred, target_names=['DOWN', 'UP']))
        
        # Confusion matrix
        print("\n📊 Confusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(f"                Predicted")
        print(f"                DOWN    UP")
        print(f"Actual  DOWN    {cm[0,0]:<7} {cm[0,1]:<7}")
        print(f"        UP      {cm[1,0]:<7} {cm[1,1]:<7}\n")
        
        # Feature importance
        print("🔍 Top 15 Features Mais Importantes:")
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for idx, row in feature_importance.head(15).iterrows():
            print(f"  {row['feature']:<25} {row['importance']:.4f}")
        
        print("\n")
        
        # Test different thresholds
        print("🎯 ANÁLISE DE THRESHOLDS (para seletividade):\n")
        print(f"{'Threshold':<12} {'Signals':<10} {'Precision':<12} {'Recall':<10} {'F1-Score':<10}")
        print("-" * 60)
        
        thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
        best_threshold = 0.70
        best_precision = 0
        
        for thresh in thresholds:
            y_pred_thresh = (y_pred_proba >= thresh).astype(int)
            if y_pred_thresh.sum() > 0:
                from sklearn.metrics import precision_score, recall_score, f1_score
                precision = precision_score(y_test, y_pred_thresh, zero_division=0)
                recall = recall_score(y_test, y_pred_thresh, zero_division=0)
                f1 = f1_score(y_test, y_pred_thresh, zero_division=0)
                
                print(f"{thresh:<12.2f} {y_pred_thresh.sum():<10} {precision:<12.3f} {recall:<10.3f} {f1:<10.3f}")
                
                if precision > best_precision and y_pred_thresh.sum() >= 30:
                    best_precision = precision
                    best_threshold = thresh
        
        print(f"\n✅ Threshold recomendado: {best_threshold:.2f} (Precision: {best_precision:.3f})\n")
        
        # Save model
        output_dir = '/app/ml/models'
        os.makedirs(output_dir, exist_ok=True)
        
        model_path = f'{output_dir}/random_forest_h1_model.joblib'
        joblib.dump(model, model_path)
        print(f"💾 Modelo salvo: {model_path}")
        
        # Save report
        report = {
            'model_type': 'RandomForestClassifier',
            'timeframe': 'H1',
            'target_hours_ahead': TARGET_HOURS_AHEAD,
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'train_period': f"{train_df['ts'].min()} - {train_df['ts'].max()}",
            'test_period': f"{test_df['ts'].min()} - {test_df['ts'].max()}",
            'features': feature_cols,
            'feature_importance': feature_importance.to_dict('records'),
            'recommended_threshold': best_threshold,
            'best_precision': float(best_precision),
            'confusion_matrix': cm.tolist(),
            'training_date': datetime.now().isoformat()
        }
        
        report_path = f'{output_dir}/model_h1_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Relatório salvo: {report_path}\n")
        
        print("="*70)
        print("✅ TREINAMENTO CONCLUÍDO COM SUCESSO!")
        print("="*70)
        print(f"\n🎯 Próximo passo: Backtest conservador com threshold {best_threshold:.2f}\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
