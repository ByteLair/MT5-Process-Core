#!/usr/bin/env python3
"""
Otimização da Estratégia H1 - Grid Search Completo

Objetivo: Atingir 52%+ win rate através de otimização de:
1. Threshold (precision vs recall)
2. Risk/Reward ratio
3. Filtros de qualidade (sessão, volatilidade, tendência)
4. Stop Loss otimizado

Status atual:
- Win rate: 49.3% (precisa +2.7%)
- ROI: -2.99% (quase break-even)
- Max DD: -13.55% (excelente)

Autor: System Optimization
Data: Nov 2025
"""

import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import joblib
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# ==================== CONFIGURAÇÕES BASE ====================

DB_CONFIG = {
    'host': 'mt5_db',  # Nome do serviço Docker
    'port': 5432,
    'database': 'mt5_trading',
    'user': 'trader',
    'password': 'trader123'
}

# Capital e risco
INITIAL_CAPITAL = 10000
RISK_PER_TRADE = 0.01  # 1%

# Custos XM (Market Maker)
SPREAD_PIPS = 1.5
SLIPPAGE_PIPS = 0.5
COMMISSION_PCT = 0.0  # XM não cobra comissão

# Grid search parameters
THRESHOLDS = [0.55, 0.60, 0.65, 0.70, 0.75]
RISK_REWARDS = [
    (20, 20),   # 1:1
    (20, 25),   # 1:1.25
    (20, 30),   # 1:1.5
    (20, 40),   # 1:2
    (15, 20),   # 1:1.33 (SL menor)
    (15, 25),   # 1:1.67
]

# Filtros de qualidade
FILTERS_CONFIG = {
    'none': {},
    'session': {'london_ny_only': True},
    'volatility': {'min_atr': 0.0015},
    'trend': {'min_adx': 20},
    'combined': {
        'london_ny_only': True,
        'min_atr': 0.0015,
        'min_adx': 20
    }
}

MAX_TRADES_PER_DAY = 3


# ==================== FUNÇÕES AUXILIARES ====================

def get_db_connection():
    """Conecta ao PostgreSQL (retorna connection string)"""
    return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"


def load_h1_data() -> pd.DataFrame:
    """Carrega dados H1 com indicadores para backtest (Oct-Nov 2025)"""
    print("📊 Carregando dados H1 com indicadores...")
    
    conn_str = get_db_connection()
    query = """
        SELECT 
            ts as time,
            open, high, low, close, volume,
            rsi, macd, macd_signal, macd_hist,
            bb_upper, bb_middle, bb_lower,
            atr
        FROM market_data
        WHERE symbol = 'EURUSD'
          AND timeframe = 'H1'
          AND ts >= '2025-10-01'
          AND ts < '2025-12-01'
          AND rsi IS NOT NULL
        ORDER BY ts
    """
    
    df = pd.read_sql(query, conn_str)
    
    print(f"  Colunas: {df.columns.tolist()}")
    print(f"  Shape: {df.shape}")
    
    # Converter coluna time para datetime se necessário
    if df['time'].dtype == 'object':
        df['time'] = pd.to_datetime(df['time'])
    
    # Converter colunas numéricas
    numeric_cols = ['open', 'high', 'low', 'close', 'volume', 
                    'rsi', 'macd', 'macd_signal', 'macd_hist',
                    'bb_upper', 'bb_middle', 'bb_lower', 'atr']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Criar features EXATAMENTE como no treinamento
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
    
    # Time features (important for H1) - usar 'time' ao invés de 'ts'
    df['hour'] = df['time'].dt.hour
    df['day_of_week'] = df['time'].dt.dayofweek
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
    
    # Filtro adicional para aplicar nos backtests
    df['is_london_ny'] = df['is_overlap']  # Usar o mesmo já calculado
    
    # ADX simplificado para filtros (usando ATR)
    df['adx'] = df['atr'].rolling(window=14).mean() / df['close'] * 100
    
    df = df.dropna()
    print(f"✅ {len(df)} candles carregados (Oct-Nov 2025)")
    
    return df


def apply_filters(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    """Aplica filtros de qualidade nos sinais"""
    filtered = df.copy()
    
    if filters.get('london_ny_only'):
        filtered = filtered[filtered['is_london_ny'] == 1]
    
    if filters.get('min_atr'):
        filtered = filtered[filtered['atr_normalized'] >= filters['min_atr']]
    
    if filters.get('min_adx'):
        filtered = filtered[filtered['adx'] >= filters['min_adx']]
    
    if filters.get('max_spread'):
        # Simular: skip se spread > max
        pass  # Já considerado no custo fixo
    
    return filtered


def calculate_position_size(capital: float, risk: float, sl_pips: float) -> float:
    """Calcula tamanho da posição baseado no risco"""
    risk_amount = capital * risk
    pip_value = 10  # USD por pip para lote padrão
    position_size = risk_amount / (sl_pips * pip_value)
    return max(0.01, min(position_size, 10.0))  # Min 0.01, max 10 lotes


def simulate_trade(
    entry_price: float,
    direction: int,  # 1=buy, -1=sell
    sl_pips: float,
    tp_pips: float,
    position_size: float,
    high_prices: np.ndarray,
    low_prices: np.ndarray
) -> Tuple[str, float]:
    """
    Simula execução do trade considerando SL e TP
    
    Returns:
        (exit_type, pnl_pips)
    """
    pip_value = 10 * position_size
    spread_cost = SPREAD_PIPS * pip_value
    slippage_cost = SLIPPAGE_PIPS * pip_value
    
    if direction == 1:  # BUY
        entry_adjusted = entry_price + (SPREAD_PIPS + SLIPPAGE_PIPS) * 0.0001
        sl_price = entry_price - sl_pips * 0.0001
        tp_price = entry_price + tp_pips * 0.0001
        
        # Check se hit SL ou TP nos próximos candles
        for i in range(len(low_prices)):
            if low_prices[i] <= sl_price:
                pnl_pips = -sl_pips
                pnl_usd = pnl_pips * pip_value - spread_cost - slippage_cost
                return ('SL', pnl_usd)
            if high_prices[i] >= tp_price:
                pnl_pips = tp_pips
                pnl_usd = pnl_pips * pip_value - spread_cost - slippage_cost
                return ('TP', pnl_usd)
        
        # Fechou no final sem hit
        close_pips = (low_prices[-1] - entry_adjusted) / 0.0001
        pnl_usd = close_pips * pip_value - spread_cost - slippage_cost
        return ('TIMEOUT', pnl_usd)
    
    else:  # SELL
        entry_adjusted = entry_price - (SPREAD_PIPS + SLIPPAGE_PIPS) * 0.0001
        sl_price = entry_price + sl_pips * 0.0001
        tp_price = entry_price - tp_pips * 0.0001
        
        for i in range(len(high_prices)):
            if high_prices[i] >= sl_price:
                pnl_pips = -sl_pips
                pnl_usd = pnl_pips * pip_value - spread_cost - slippage_cost
                return ('SL', pnl_usd)
            if low_prices[i] <= tp_price:
                pnl_pips = tp_pips
                pnl_usd = pnl_pips * pip_value - spread_cost - slippage_cost
                return ('TP', pnl_usd)
        
        close_pips = (entry_adjusted - high_prices[-1]) / 0.0001
        pnl_usd = close_pips * pip_value - spread_cost - slippage_cost
        return ('TIMEOUT', pnl_usd)


def backtest_configuration(
    df: pd.DataFrame,
    model,
    threshold: float,
    sl_pips: float,
    tp_pips: float,
    filters: Dict,
    filter_name: str
) -> Dict:
    """
    Executa backtest com configuração específica
    
    Returns:
        Dict com métricas de performance
    """
    # Aplicar filtros
    df_filtered = apply_filters(df, filters)
    
    if len(df_filtered) < 30:
        return {
            'threshold': threshold,
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'rr_ratio': tp_pips / sl_pips,
            'filter': filter_name,
            'valid': False,
            'reason': 'Dados insuficientes após filtros'
        }
    
    # Preparar features para predição (MESMAS do treinamento!)
    feature_cols = [
        'returns', 'high_low_range', 'close_open_range',
        'rsi', 'macd', 'macd_signal', 'macd_hist',
        'bb_position', 'bb_width',
        'macd_trend', 'macd_momentum',
        'rsi_oversold', 'rsi_overbought', 'rsi_neutral',
        'atr_normalized',
        'hour', 'day_of_week',
        'is_london_session', 'is_ny_session', 'is_overlap',
        'price_above_bb_mid', 'macd_above_zero',
        'returns_roll_mean_5', 'returns_roll_std_5', 'volume_roll_mean_5'
    ]
    
    X = df_filtered[feature_cols].copy()
    X = X.fillna(method='ffill').fillna(0)
    
    # Gerar predições
    try:
        proba = model.predict_proba(X)[:, 1]
    except:
        return {
            'threshold': threshold,
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'rr_ratio': tp_pips / sl_pips,
            'filter': filter_name,
            'valid': False,
            'reason': 'Erro na predição do modelo'
        }
    
    df_filtered['signal_proba'] = proba
    df_filtered['signal'] = (proba >= threshold).astype(int)
    
    # Simular trades
    capital = INITIAL_CAPITAL
    trades = []
    equity_curve = [capital]
    trades_today = {}
    
    for idx in range(len(df_filtered) - 1):
        row = df_filtered.iloc[idx]
        
        if row['signal'] == 0:
            equity_curve.append(capital)
            continue
        
        # Controlar max trades por dia
        trade_date = pd.to_datetime(row['time']).date()
        trades_today[trade_date] = trades_today.get(trade_date, 0)
        
        if trades_today[trade_date] >= MAX_TRADES_PER_DAY:
            equity_curve.append(capital)
            continue
        
        # Calcular position size
        position_size = calculate_position_size(capital, RISK_PER_TRADE, sl_pips)
        
        # Determinar direção (simplificado: buy se MACD positivo)
        direction = 1 if row['macd'] > 0 else -1
        
        # Simular trade nos próximos 5 candles
        future_highs = df_filtered.iloc[idx+1:idx+6]['high'].values
        future_lows = df_filtered.iloc[idx+1:idx+6]['low'].values
        
        if len(future_highs) == 0:
            equity_curve.append(capital)
            continue
        
        exit_type, pnl = simulate_trade(
            row['close'],
            direction,
            sl_pips,
            tp_pips,
            position_size,
            future_highs,
            future_lows
        )
        
        capital += pnl
        trades_today[trade_date] += 1
        
        trades.append({
            'time': row['time'],
            'direction': 'BUY' if direction == 1 else 'SELL',
            'entry': row['close'],
            'exit_type': exit_type,
            'pnl': pnl,
            'capital': capital,
            'position_size': position_size,
            'signal_proba': row['signal_proba']
        })
        
        equity_curve.append(capital)
    
    # Calcular métricas
    if len(trades) < 10:
        return {
            'threshold': threshold,
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'rr_ratio': tp_pips / sl_pips,
            'filter': filter_name,
            'valid': False,
            'reason': f'Poucos trades: {len(trades)}'
        }
    
    trades_df = pd.DataFrame(trades)
    
    # Win rate
    wins = trades_df[trades_df['exit_type'] == 'TP']
    losses = trades_df[trades_df['exit_type'] == 'SL']
    win_rate = len(wins) / len(trades_df) if len(trades_df) > 0 else 0
    
    # Profit factor
    total_wins = wins['pnl'].sum() if len(wins) > 0 else 0
    total_losses = abs(losses['pnl'].sum()) if len(losses) > 0 else 1
    profit_factor = total_wins / total_losses if total_losses > 0 else 0
    
    # ROI
    roi = ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100
    
    # Max Drawdown
    equity_series = pd.Series(equity_curve)
    cummax = equity_series.cummax()
    drawdown = (equity_series - cummax) / cummax * 100
    max_dd = drawdown.min()
    
    # Sharpe (simplificado)
    returns = trades_df['pnl'] / INITIAL_CAPITAL
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    
    # Avg trade duration
    avg_win = wins['pnl'].mean() if len(wins) > 0 else 0
    avg_loss = losses['pnl'].mean() if len(losses) > 0 else 0
    
    return {
        'threshold': threshold,
        'sl_pips': sl_pips,
        'tp_pips': tp_pips,
        'rr_ratio': tp_pips / sl_pips,
        'filter': filter_name,
        'valid': True,
        'total_trades': len(trades_df),
        'win_rate': win_rate * 100,
        'wins': len(wins),
        'losses': len(losses),
        'roi': roi,
        'profit_factor': profit_factor,
        'max_dd': max_dd,
        'sharpe': sharpe,
        'final_capital': capital,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'total_pnl': capital - INITIAL_CAPITAL,
        # Critérios de viabilidade
        'meets_winrate': win_rate >= 0.52,
        'meets_roi': roi > 0,
        'meets_dd': max_dd >= -20,
        'meets_pf': profit_factor >= 1.5,
        'meets_sharpe': sharpe >= 1.0,
        'meets_trades': len(trades_df) >= 30,
        'criteria_met': sum([
            win_rate >= 0.52,
            roi > 0,
            max_dd >= -20,
            profit_factor >= 1.5,
            sharpe >= 1.0,
            len(trades_df) >= 30
        ])
    }


def run_optimization():
    """Executa grid search completo"""
    print("\n" + "="*80)
    print("🔍 INICIANDO OTIMIZAÇÃO DA ESTRATÉGIA H1")
    print("="*80)
    
    # Carregar modelo
    print("\n📦 Carregando modelo H1...")
    model = joblib.load('/app/ml/models/random_forest_h1_model.joblib')
    print("✅ Modelo carregado")
    
    # Carregar dados
    df = load_h1_data()
    
    # Grid search
    results = []
    total_configs = len(THRESHOLDS) * len(RISK_REWARDS) * len(FILTERS_CONFIG)
    current = 0
    
    print(f"\n🔄 Testando {total_configs} configurações...\n")
    
    for threshold in THRESHOLDS:
        for sl_pips, tp_pips in RISK_REWARDS:
            for filter_name, filters in FILTERS_CONFIG.items():
                current += 1
                
                print(f"[{current}/{total_configs}] Threshold={threshold:.2f}, "
                      f"SL/TP={sl_pips}/{tp_pips}, Filter={filter_name}...", end=' ')
                
                result = backtest_configuration(
                    df, model, threshold, sl_pips, tp_pips, filters, filter_name
                )
                
                if result['valid']:
                    print(f"✅ WR={result['win_rate']:.1f}%, ROI={result['roi']:.1f}%, "
                          f"Trades={result['total_trades']}")
                else:
                    print(f"❌ {result['reason']}")
                
                results.append(result)
    
    return results


def print_results(results: List[Dict]):
    """Imprime resultados formatados"""
    valid_results = [r for r in results if r.get('valid', False)]
    
    if not valid_results:
        print("\n❌ Nenhuma configuração válida encontrada!")
        return
    
    # Ordenar por critérios atendidos, depois win rate
    valid_results.sort(key=lambda x: (x['criteria_met'], x['win_rate']), reverse=True)
    
    print("\n" + "="*80)
    print("📊 TOP 10 MELHORES CONFIGURAÇÕES")
    print("="*80)
    
    for i, r in enumerate(valid_results[:10], 1):
        print(f"\n🏆 RANK #{i}")
        print(f"{'─'*80}")
        print(f"  Threshold:      {r['threshold']:.2f}")
        print(f"  SL/TP:          {r['sl_pips']:.0f}/{r['tp_pips']:.0f} pips (RR 1:{r['rr_ratio']:.2f})")
        print(f"  Filtros:        {r['filter']}")
        print(f"")
        print(f"  💰 ROI:          {r['roi']:+.2f}% {'✅' if r['roi'] > 0 else '❌'}")
        print(f"  🎯 Win Rate:     {r['win_rate']:.1f}% {'✅' if r['win_rate'] >= 52 else '❌'}")
        print(f"  📊 Profit Factor: {r['profit_factor']:.2f} {'✅' if r['profit_factor'] >= 1.5 else '❌'}")
        print(f"  📉 Max DD:       {r['max_dd']:.2f}% {'✅' if r['max_dd'] >= -20 else '❌'}")
        print(f"  📈 Sharpe:       {r['sharpe']:.2f} {'✅' if r['sharpe'] >= 1.0 else '❌'}")
        print(f"  🔢 Trades:       {r['total_trades']} {'✅' if r['total_trades'] >= 30 else '❌'}")
        print(f"")
        print(f"  Wins:   {r['wins']} × ${r['avg_win']:.2f} = ${r['wins'] * r['avg_win']:.2f}")
        print(f"  Losses: {r['losses']} × ${r['avg_loss']:.2f} = ${r['losses'] * r['avg_loss']:.2f}")
        print(f"  Net P&L: ${r['total_pnl']:+.2f}")
        print(f"")
        print(f"  ⭐ Critérios atendidos: {r['criteria_met']}/6")
    
    # Estatísticas gerais
    print("\n" + "="*80)
    print("📈 ESTATÍSTICAS GERAIS")
    print("="*80)
    
    win_rates = [r['win_rate'] for r in valid_results]
    rois = [r['roi'] for r in valid_results]
    
    print(f"\n  Win Rate:")
    print(f"    Melhor:  {max(win_rates):.1f}%")
    print(f"    Pior:    {min(win_rates):.1f}%")
    print(f"    Média:   {np.mean(win_rates):.1f}%")
    print(f"")
    print(f"  ROI:")
    print(f"    Melhor:  {max(rois):+.2f}%")
    print(f"    Pior:    {min(rois):+.2f}%")
    print(f"    Média:   {np.mean(rois):+.2f}%")
    print(f"")
    print(f"  Configs que atingiram 52%+ win rate: {sum(1 for r in valid_results if r['win_rate'] >= 52)}")
    print(f"  Configs lucrativas (ROI > 0):        {sum(1 for r in valid_results if r['roi'] > 0)}")
    print(f"  Configs com 4+ critérios:            {sum(1 for r in valid_results if r['criteria_met'] >= 4)}")
    
    # Melhor config
    best = valid_results[0]
    print("\n" + "="*80)
    print("🎯 RECOMENDAÇÃO FINAL")
    print("="*80)
    
    if best['criteria_met'] >= 4 and best['win_rate'] >= 52:
        print("\n✅ SISTEMA VIÁVEL! Configuração recomendada:")
    elif best['roi'] > 0:
        print("\n⚠️  SISTEMA POTENCIALMENTE VIÁVEL. Configuração recomendada:")
    else:
        print("\n❌ Sistema ainda não atingiu viabilidade. Melhor configuração até agora:")
    
    print(f"\n  📋 PARÂMETROS:")
    print(f"     Threshold: {best['threshold']:.2f}")
    print(f"     Stop Loss: {best['sl_pips']:.0f} pips")
    print(f"     Take Profit: {best['tp_pips']:.0f} pips (RR 1:{best['rr_ratio']:.2f})")
    print(f"     Filtros: {best['filter']}")
    print(f"")
    print(f"  📊 PERFORMANCE:")
    print(f"     Win Rate: {best['win_rate']:.1f}%")
    print(f"     ROI: {best['roi']:+.2f}%")
    print(f"     Profit Factor: {best['profit_factor']:.2f}")
    print(f"     Max DD: {best['max_dd']:.2f}%")
    print(f"     Sharpe: {best['sharpe']:.2f}")
    print(f"     Trades: {best['total_trades']}")
    print(f"")
    print(f"  🎯 Critérios atendidos: {best['criteria_met']}/6")
    
    if best['win_rate'] >= 52:
        print("\n  🎉 META DE 52% WIN RATE ATINGIDA! 🎉")
    else:
        diff = 52 - best['win_rate']
        print(f"\n  ⚠️  Faltam {diff:.1f}% para atingir meta de 52%")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    results = run_optimization()
    
    # Salvar resultados
    results_df = pd.DataFrame([r for r in results if r.get('valid', False)])
    results_df.to_csv('/app/ml/models/optimization_results_h1.csv', index=False)
    print(f"\n💾 Resultados salvos em: /app/ml/models/optimization_results_h1.csv")
    
    # Imprimir relatório
    print_results(results)
    
    print("\n✅ Otimização concluída!\n")
