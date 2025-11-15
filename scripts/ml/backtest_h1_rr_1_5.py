#!/usr/bin/env python3
"""
Backtest H1 - TESTE RR 1:1.5
- RR 1:1.5 (20 pips SL = 30 pips TP)
- Máximo 3 trades por dia
- 1% risco por trade
- Threshold 0.55
- Custos reais: spread + slippage + commission XM
"""
import os
import sys
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
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

# Backtest configuration - TESTE RR 1:1.5
INITIAL_CAPITAL = 10000
RISK_PER_TRADE = 0.01  # 1% do capital
STOP_LOSS_PIPS = 20
TAKE_PROFIT_PIPS = 30  # RR 1:1.5 ✨
MAX_TRADES_PER_DAY = 3

# Real costs
SPREAD_PIPS = 1.5
SLIPPAGE_PIPS = 0.5
COMMISSION_PCT = 0.0  # XM Standard = 0% (Market Maker, lucra no spread)

# Model configuration
THRESHOLD = 0.55  # Alta seletividade
TARGET_HOURS_AHEAD = 4

def create_features(df):
    """Create same features as training"""
    df['returns'] = df['close'].pct_change()
    df['high_low_range'] = (df['high'] - df['low']) / df['close']
    df['close_open_range'] = (df['close'] - df['open']) / df['open']
    
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    df['macd_trend'] = (df['macd'] > df['macd_signal']).astype(int)
    df['macd_momentum'] = df['macd'] - df['macd_signal']
    
    df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
    df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
    df['rsi_neutral'] = ((df['rsi'] >= 40) & (df['rsi'] <= 60)).astype(int)
    
    df['atr_normalized'] = df['atr'] / df['close']
    
    df['hour'] = pd.to_datetime(df['ts']).dt.hour
    df['day_of_week'] = pd.to_datetime(df['ts']).dt.dayofweek
    df['is_london_session'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)
    df['is_ny_session'] = ((df['hour'] >= 13) & (df['hour'] < 21)).astype(int)
    df['is_overlap'] = ((df['hour'] >= 13) & (df['hour'] < 16)).astype(int)
    
    df['price_above_bb_mid'] = (df['close'] > df['bb_middle']).astype(int)
    df['macd_above_zero'] = (df['macd'] > 0).astype(int)
    
    df['returns_roll_mean_5'] = df['returns'].rolling(5).mean()
    df['returns_roll_std_5'] = df['returns'].rolling(5).std()
    df['volume_roll_mean_5'] = df['volume'].rolling(5).mean()
    
    return df

def calculate_position_size(capital, risk_pct, stop_loss_pips, pip_value=10):
    """Calculate position size based on risk"""
    risk_amount = capital * risk_pct
    position_size = risk_amount / (stop_loss_pips * pip_value)
    return max(0.01, round(position_size, 2))  # Min 0.01 lote

def simulate_trade(entry_price, direction, stop_loss_pips, take_profit_pips, 
                   future_prices, spread_pips=1.5, slippage_pips=0.5):
    """
    Simulate trade execution with realistic fills
    Returns: (exit_price, exit_reason, pips_result)
    """
    pip_size = 0.0001
    
    # Apply spread and slippage on entry
    if direction == 'BUY':
        actual_entry = entry_price + (spread_pips + slippage_pips) * pip_size
        stop_loss_price = actual_entry - stop_loss_pips * pip_size
        take_profit_price = actual_entry + take_profit_pips * pip_size
    else:
        actual_entry = entry_price - (spread_pips + slippage_pips) * pip_size
        stop_loss_price = actual_entry + stop_loss_pips * pip_size
        take_profit_price = actual_entry - take_profit_pips * pip_size
    
    # Check each candle for SL/TP hit
    for candle in future_prices:
        if direction == 'BUY':
            # Check stop loss first (conservative)
            if candle['low'] <= stop_loss_price:
                exit_price = stop_loss_price - slippage_pips * pip_size
                pips = (exit_price - actual_entry) / pip_size
                return exit_price, 'STOP_LOSS', pips
            # Check take profit
            if candle['high'] >= take_profit_price:
                exit_price = take_profit_price - slippage_pips * pip_size
                pips = (exit_price - actual_entry) / pip_size
                return exit_price, 'TAKE_PROFIT', pips
        else:  # SELL
            # Check stop loss first
            if candle['high'] >= stop_loss_price:
                exit_price = stop_loss_price + slippage_pips * pip_size
                pips = (actual_entry - exit_price) / pip_size
                return exit_price, 'STOP_LOSS', pips
            # Check take profit
            if candle['low'] <= take_profit_price:
                exit_price = take_profit_price + slippage_pips * pip_size
                pips = (actual_entry - exit_price) / pip_size
                return exit_price, 'TAKE_PROFIT', pips
    
    # Trade still open (shouldn't happen with proper horizon)
    return actual_entry, 'TIMEOUT', 0

def main():
    print("\n" + "="*80)
    print("🔬 BACKTEST H1 - CONSERVADOR (OUT-OF-SAMPLE)")
    print("="*80 + "\n")
    
    try:
        # Load model
        model_path = '/app/ml/models/random_forest_h1_model.joblib'
        print(f"📂 Carregando modelo: {model_path}")
        model = joblib.load(model_path)
        print("✅ Modelo carregado!\n")
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Load test data (Oct-Nov 2025)
        print("📊 Carregando dados de teste (Out-Nov 2025)...")
        query = """
            SELECT ts, open, high, low, close, volume,
                   rsi, macd, macd_signal, macd_hist,
                   bb_upper, bb_middle, bb_lower, atr
            FROM market_data
            WHERE symbol = 'EURUSD'
            AND timeframe = 'H1'
            AND ts >= '2025-10-01'
            AND rsi IS NOT NULL
            ORDER BY ts ASC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        print(f"✅ {len(df):,} candles carregados")
        print(f"📅 Período: {df['ts'].min()} até {df['ts'].max()}\n")
        
        # Create features
        print("🔧 Preparando features...")
        df = create_features(df)
        df = df.dropna()
        print(f"✅ {len(df):,} candles prontos\n")
        
        # Feature columns (must match training)
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
        
        # Generate predictions
        print("🤖 Gerando predições...")
        X = df[feature_cols]
        df['prediction_proba'] = model.predict_proba(X)[:, 1]
        df['signal'] = (df['prediction_proba'] >= THRESHOLD).astype(int)
        
        print(f"✅ Total de sinais gerados: {df['signal'].sum():,}\n")
        
        # Run backtest
        print("="*80)
        print("💼 EXECUTANDO BACKTEST")
        print("="*80)
        print(f"\n📋 CONFIGURAÇÃO:")
        print(f"  • Capital inicial: ${INITIAL_CAPITAL:,.2f}")
        print(f"  • Risco por trade: {RISK_PER_TRADE*100:.1f}%")
        print(f"  • Stop Loss: {STOP_LOSS_PIPS} pips")
        print(f"  • Take Profit: {TAKE_PROFIT_PIPS} pips (RR 1:1)")
        print(f"  • Máx trades/dia: {MAX_TRADES_PER_DAY}")
        print(f"  • Threshold: {THRESHOLD:.2f}")
        print(f"  • Spread: {SPREAD_PIPS} pips")
        print(f"  • Slippage: {SLIPPAGE_PIPS} pips")
        print(f"  • Comissão: {COMMISSION_PCT*100:.2f}%\n")
        
        capital = INITIAL_CAPITAL
        trades = []
        daily_trades = {}
        
        for idx in range(len(df) - 50):  # Leave room for future candles
            row = df.iloc[idx]
            
            # Check if signal
            if row['signal'] == 0:
                continue
            
            # Check daily limit
            trade_date = pd.to_datetime(row['ts']).date()
            if trade_date not in daily_trades:
                daily_trades[trade_date] = 0
            
            if daily_trades[trade_date] >= MAX_TRADES_PER_DAY:
                continue  # Skip, já atingiu limite diário
            
            # Get future candles for trade simulation
            future_candles = df.iloc[idx+1:idx+51].to_dict('records')
            if len(future_candles) < 20:
                continue  # Not enough future data
            
            # Calculate position size
            position_size = calculate_position_size(
                capital, RISK_PER_TRADE, STOP_LOSS_PIPS
            )
            
            # Simulate trade (sempre BUY em H1 swing)
            exit_price, exit_reason, pips = simulate_trade(
                entry_price=row['close'],
                direction='BUY',
                stop_loss_pips=STOP_LOSS_PIPS,
                take_profit_pips=TAKE_PROFIT_PIPS,
                future_prices=future_candles,
                spread_pips=SPREAD_PIPS,
                slippage_pips=SLIPPAGE_PIPS
            )
            
            # Calculate P&L
            pip_value = 10  # $10 per pip for 1 lote
            gross_pnl = pips * pip_value * position_size
            commission = abs(row['close'] * position_size * 100000 * COMMISSION_PCT)
            net_pnl = gross_pnl - commission
            
            # Update capital
            capital += net_pnl
            daily_trades[trade_date] += 1
            
            # Record trade
            trades.append({
                'entry_time': row['ts'],
                'entry_price': row['close'],
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'pips': pips,
                'position_size': position_size,
                'gross_pnl': gross_pnl,
                'commission': commission,
                'net_pnl': net_pnl,
                'capital': capital,
                'probability': row['prediction_proba']
            })
        
        # Analysis
        trades_df = pd.DataFrame(trades)
        
        if len(trades_df) == 0:
            print("❌ Nenhum trade executado!")
            return
        
        # Calculate metrics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['net_pnl'] > 0])
        losing_trades = len(trades_df[trades_df['net_pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_gross_profit = trades_df[trades_df['gross_pnl'] > 0]['gross_pnl'].sum()
        total_gross_loss = abs(trades_df[trades_df['gross_pnl'] < 0]['gross_pnl'].sum())
        profit_factor = total_gross_profit / total_gross_loss if total_gross_loss > 0 else 0
        
        total_commission = trades_df['commission'].sum()
        net_profit = capital - INITIAL_CAPITAL
        roi = (net_profit / INITIAL_CAPITAL) * 100
        
        # Drawdown
        trades_df['cumulative_capital'] = trades_df['capital']
        trades_df['peak'] = trades_df['cumulative_capital'].cummax()
        trades_df['drawdown'] = ((trades_df['cumulative_capital'] - trades_df['peak']) / 
                                  trades_df['peak'] * 100)
        max_drawdown = trades_df['drawdown'].min()
        
        # Sharpe Ratio (approximation)
        returns = trades_df['net_pnl'] / INITIAL_CAPITAL
        sharpe = (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        
        # Test days
        test_days = (df['ts'].max() - df['ts'].min()).days
        trades_per_day = total_trades / test_days if test_days > 0 else 0
        
        print("="*80)
        print("📊 RESULTADOS DO BACKTEST")
        print("="*80 + "\n")
        
        print("💰 PERFORMANCE FINANCEIRA:")
        print(f"  • Capital Inicial:      ${INITIAL_CAPITAL:,.2f}")
        print(f"  • Capital Final:        ${capital:,.2f}")
        print(f"  • Lucro/Prejuízo:       ${net_profit:,.2f}")
        print(f"  • ROI:                  {roi:+.2f}%")
        print(f"  • Max Drawdown:         {max_drawdown:.2f}%\n")
        
        print("📈 ESTATÍSTICAS DE TRADES:")
        print(f"  • Total de Trades:      {total_trades}")
        print(f"  • Trades Vencedores:    {winning_trades} ({win_rate*100:.1f}%)")
        print(f"  • Trades Perdedores:    {losing_trades} ({(1-win_rate)*100:.1f}%)")
        print(f"  • Profit Factor:        {profit_factor:.2f}")
        print(f"  • Sharpe Ratio:         {sharpe:.2f}")
        print(f"  • Trades/dia (média):   {trades_per_day:.2f}\n")
        
        print("💸 CUSTOS:")
        print(f"  • Total Comissões:      ${total_commission:,.2f}")
        print(f"  • Spread/Slippage:      ~${(SPREAD_PIPS+SLIPPAGE_PIPS)*10*total_trades:,.2f}")
        print(f"  • Custos Totais:        ~${total_commission + (SPREAD_PIPS+SLIPPAGE_PIPS)*10*total_trades:,.2f}\n")
        
        print("🎯 ANÁLISE POR EXIT REASON:")
        exit_summary = trades_df.groupby('exit_reason').agg({
            'net_pnl': ['count', 'sum', 'mean']
        }).round(2)
        print(exit_summary)
        print()
        
        # Daily stats
        print("📅 TRADES POR DIA:")
        daily_summary = pd.DataFrame(list(daily_trades.items()), 
                                     columns=['date', 'trades'])
        print(f"  • Dias com trades:      {len(daily_summary)}")
        print(f"  • Média trades/dia:     {daily_summary['trades'].mean():.2f}")
        print(f"  • Máx trades em 1 dia:  {daily_summary['trades'].max()}\n")
        
        # Verdict
        print("="*80)
        print("🎯 VEREDITO")
        print("="*80 + "\n")
        
        criteria = {
            'Win Rate ≥ 60%': win_rate >= 0.60,
            'Sharpe Ratio ≥ 1.5': sharpe >= 1.5,
            'Max Drawdown ≤ 20%': max_drawdown >= -20,
            'Profit Factor ≥ 2.0': profit_factor >= 2.0,
            'ROI > 0%': roi > 0,
            'Trades suficientes (≥30)': total_trades >= 30
        }
        
        passed = sum(criteria.values())
        total_criteria = len(criteria)
        
        for criterion, result in criteria.items():
            symbol = "✅" if result else "❌"
            print(f"  {symbol} {criterion}")
        
        print(f"\n📊 Critérios atendidos: {passed}/{total_criteria}\n")
        
        if passed >= 4:
            print("✅ SISTEMA VIÁVEL para paper trading!")
            print("   Recomendação: Prosseguir para validação em conta demo\n")
        elif passed >= 2:
            print("⚠️  SISTEMA PARCIALMENTE VIÁVEL")
            print("   Recomendação: Otimizar parâmetros antes de paper trading\n")
        else:
            print("❌ SISTEMA NÃO VIÁVEL")
            print("   Recomendação: Revisar estratégia ou modelo\n")
        
        # Save results
        output_dir = '/app/ml/models'
        
        # Save trades CSV
        trades_csv_path = f'{output_dir}/backtest_h1_trades.csv'
        trades_df.to_csv(trades_csv_path, index=False)
        print(f"💾 Trades salvos: {trades_csv_path}")
        
        # Save summary JSON
        summary = {
            'backtest_date': datetime.now().isoformat(),
            'period': f"{df['ts'].min()} - {df['ts'].max()}",
            'config': {
                'initial_capital': INITIAL_CAPITAL,
                'risk_per_trade': RISK_PER_TRADE,
                'stop_loss_pips': STOP_LOSS_PIPS,
                'take_profit_pips': TAKE_PROFIT_PIPS,
                'max_trades_per_day': MAX_TRADES_PER_DAY,
                'threshold': THRESHOLD,
                'spread_pips': SPREAD_PIPS,
                'slippage_pips': SLIPPAGE_PIPS,
                'commission_pct': COMMISSION_PCT
            },
            'results': {
                'final_capital': float(capital),
                'net_profit': float(net_profit),
                'roi_pct': float(roi),
                'total_trades': int(total_trades),
                'winning_trades': int(winning_trades),
                'losing_trades': int(losing_trades),
                'win_rate_pct': float(win_rate * 100),
                'profit_factor': float(profit_factor),
                'sharpe_ratio': float(sharpe),
                'max_drawdown_pct': float(max_drawdown),
                'trades_per_day': float(trades_per_day),
                'total_commission': float(total_commission)
            },
            'criteria_passed': criteria,
            'verdict': 'VIABLE' if passed >= 4 else 'PARTIAL' if passed >= 2 else 'NOT_VIABLE'
        }
        
        summary_path = f'{output_dir}/backtest_h1_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"📄 Resumo salvo: {summary_path}\n")
        
        print("="*80)
        print("✅ BACKTEST CONCLUÍDO!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
