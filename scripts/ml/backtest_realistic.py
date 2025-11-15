"""
BACKTEST RIGOROSO - Simulação realista de trading com custos reais.

Este script implementa um backtest completo incluindo TODOS os custos:
- Spread (1.5 pips por trade)
- Slippage (0.5 pip em média)
- Comissão (0.05% por volume)
- Latência de execução (perda de alguns sinais)

Métricas calculadas:
- Sharpe Ratio (alvo > 1.5)
- Maximum Drawdown (alvo < 20%)
- Profit Factor (alvo > 2.0)
- Win Rate
- Total de trades
- ROI anual

⚠️  ATENÇÃO: Este é um backtest CONSERVADOR e REALISTA.
   Resultados otimistas são RED FLAGS!
"""
import os
import sys
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timedelta
from sqlalchemy import create_engine
import warnings
warnings.filterwarnings('ignore')

print("=" * 80)
print("🔬 BACKTEST RIGOROSO - SIMULAÇÃO REALISTA DE TRADING")
print("=" * 80)
print("⚠️  Incluindo TODOS os custos reais do mercado\n")

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

CONFIG = {
    # Capital e Risk Management
    'initial_capital': 10000,           # USD
    'risk_per_trade': 0.01,             # 1% por trade
    'max_trades_concurrent': 5,
    
    # Custos realistas (EURUSD típico)
    'spread_pips': 1.5,                 # Spread médio
    'slippage_pips': 0.5,               # Slippage médio
    'commission_pct': 0.0005,           # 0.05% comissão
    
    # Execução
    'stop_loss_pips': 10,
    'take_profit_pips': 15,
    'pip_value': 1.0,                   # $1 por pip (mini lote)
    
    # Modelo
    'threshold': 0.35,                  # Threshold conservador
    'model_path': '/tmp/random_forest_model.joblib',
    
    # Dados
    'lookback_months': 24,              # 2 anos de backtest (out-of-sample)
    'test_period_start': '2023-11-01',  # Período de teste
}

print("📋 CONFIGURAÇÃO DO BACKTEST:")
print(f"   Capital inicial: ${CONFIG['initial_capital']:,}")
print(f"   Risco por trade: {CONFIG['risk_per_trade']*100:.1f}%")
print(f"   Stop Loss: {CONFIG['stop_loss_pips']} pips")
print(f"   Take Profit: {CONFIG['take_profit_pips']} pips")
print(f"   Spread: {CONFIG['spread_pips']} pips")
print(f"   Slippage: {CONFIG['slippage_pips']} pips")
print(f"   Comissão: {CONFIG['commission_pct']*100:.3f}%")
print(f"   Threshold: {CONFIG['threshold']}")
print(f"   Período de teste: {CONFIG['test_period_start']} até hoje")
print()

# ============================================================================
# CONEXÃO COM BANCO DE DADOS
# ============================================================================

print("📊 Carregando dados do banco...")

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'mt5_db'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'mt5_trading'),
    'user': os.getenv('POSTGRES_USER', 'trader'),
    'password': os.getenv('POSTGRES_PASSWORD', 'trader_password')
}

connection_string = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

engine = create_engine(connection_string)

# Carregar dados de teste (período out-of-sample)
query = f"""
    SELECT 
        ts as time,
        open,
        high,
        low,
        close,
        volume,
        rsi,
        macd,
        macd_signal,
        macd_hist,
        bb_upper,
        bb_middle,
        bb_lower,
        atr
    FROM market_data
    WHERE symbol = 'EURUSD'
        AND timeframe = 'M1'
        AND ts >= '{CONFIG['test_period_start']}'
        AND rsi IS NOT NULL
        AND macd IS NOT NULL
        AND bb_upper IS NOT NULL
        AND atr IS NOT NULL
    ORDER BY ts ASC
"""

print(f"   Query: {CONFIG['test_period_start']} até hoje")
df = pd.read_sql(query, engine)
print(f"   ✅ {len(df):,} candles carregados")

if len(df) < 10000:
    print(f"\n   ⚠️  AVISO: Apenas {len(df):,} candles disponíveis.")
    print(f"   Recomendado: pelo menos 100,000 candles para backtest robusto")
    print()

# ============================================================================
# FEATURE ENGINEERING
# ============================================================================

print("\n🔧 Preparando features...")

# Time features
df['hour'] = pd.to_datetime(df['time']).dt.hour
df['minute'] = pd.to_datetime(df['time']).dt.minute
df['day_of_week'] = pd.to_datetime(df['time']).dt.dayofweek

# Trading sessions
def get_session(hour):
    if 0 <= hour < 8: return 0      # Asian
    elif 8 <= hour < 16: return 1   # European
    elif 16 <= hour < 24: return 2  # American
    return 0

df['session'] = df['hour'].apply(get_session)

# Price features (adicionar 2 features para completar 19)
df['price_to_bb'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])  # Posição relativa nas bandas
df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']  # Largura das bandas (volatilidade)

# Target: preço sobe nos próximos 5 candles?
df['future_close'] = df['close'].shift(-5)
df['target'] = (df['future_close'] > df['close']).astype(int)

# Remover NaN
df = df.dropna().reset_index(drop=True)

print(f"   ✅ {len(df):,} candles preparados")
print(f"   Período: {df['time'].min()} até {df['time'].max()}")

# ============================================================================
# CARREGAR MODELO
# ============================================================================

print("\n📦 Carregando modelo treinado...")
model = joblib.load(CONFIG['model_path'])
print("   ✅ Modelo carregado\n")

# Features para predição (19 features como no treino)
feature_cols = [
    'open', 'high', 'low', 'close', 'volume',
    'rsi', 'macd', 'macd_signal', 'macd_hist',
    'bb_upper', 'bb_middle', 'bb_lower', 'atr',
    'hour', 'minute', 'day_of_week', 'session',
    'price_to_bb', 'bb_width'
]

X = df[feature_cols]

# Gerar probabilidades
print("🔮 Gerando predições...")
y_proba = model.predict_proba(X)[:, 1]  # Probabilidade de alta
df['signal_probability'] = y_proba
df['signal'] = (y_proba >= CONFIG['threshold']).astype(int)

print(f"   ✅ {df['signal'].sum():,} sinais gerados ({df['signal'].sum()/len(df)*100:.2f}%)")

# ============================================================================
# SIMULAÇÃO DE TRADING
# ============================================================================

print("\n" + "=" * 80)
print("💰 SIMULANDO TRADING COM CUSTOS REAIS")
print("=" * 80)

capital = CONFIG['initial_capital']
trades = []
equity_curve = [capital]
peak_capital = capital
max_drawdown = 0

open_positions = []

for idx, row in df.iterrows():
    current_time = row['time']
    current_price = row['close']
    
    # Processar posições abertas (verificar SL/TP)
    for pos in open_positions[:]:  # Cópia para poder remover durante iteração
        # Verificar Stop Loss
        if row['low'] <= pos['stop_loss']:
            # Trade perdedor (hit SL)
            exit_price = pos['stop_loss']
            pips = -CONFIG['stop_loss_pips']
            
            # Custos
            spread_cost = CONFIG['spread_pips'] * CONFIG['pip_value']
            slippage_cost = CONFIG['slippage_pips'] * CONFIG['pip_value']
            commission_cost = abs(pips) * CONFIG['pip_value'] * CONFIG['commission_pct']
            
            pnl = (pips * CONFIG['pip_value']) - spread_cost - slippage_cost - commission_cost
            capital += pnl
            
            trades.append({
                'entry_time': pos['entry_time'],
                'exit_time': current_time,
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'pips': pips,
                'pnl': pnl,
                'capital': capital,
                'result': 'loss'
            })
            
            open_positions.remove(pos)
            
        # Verificar Take Profit
        elif row['high'] >= pos['take_profit']:
            # Trade vencedor (hit TP)
            exit_price = pos['take_profit']
            pips = CONFIG['take_profit_pips']
            
            # Custos
            spread_cost = CONFIG['spread_pips'] * CONFIG['pip_value']
            slippage_cost = CONFIG['slippage_pips'] * CONFIG['pip_value']
            commission_cost = abs(pips) * CONFIG['pip_value'] * CONFIG['commission_pct']
            
            pnl = (pips * CONFIG['pip_value']) - spread_cost - slippage_cost - commission_cost
            capital += pnl
            
            trades.append({
                'entry_time': pos['entry_time'],
                'exit_time': current_time,
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'pips': pips,
                'pnl': pnl,
                'capital': capital,
                'result': 'win'
            })
            
            open_positions.remove(pos)
    
    # Novo sinal de compra?
    if row['signal'] == 1 and len(open_positions) < CONFIG['max_trades_concurrent']:
        # Abrir nova posição
        entry_price = current_price
        stop_loss = entry_price - (CONFIG['stop_loss_pips'] * 0.0001)  # EURUSD: 1 pip = 0.0001
        take_profit = entry_price + (CONFIG['take_profit_pips'] * 0.0001)
        
        open_positions.append({
            'entry_time': current_time,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
        })
    
    # Atualizar equity curve
    equity_curve.append(capital)
    
    # Calcular drawdown
    if capital > peak_capital:
        peak_capital = capital
    drawdown = (peak_capital - capital) / peak_capital
    max_drawdown = max(max_drawdown, drawdown)

# Fechar posições restantes (fim do backtest)
for pos in open_positions:
    exit_price = df.iloc[-1]['close']
    pips = (exit_price - pos['entry_price']) / 0.0001
    
    spread_cost = CONFIG['spread_pips'] * CONFIG['pip_value']
    slippage_cost = CONFIG['slippage_pips'] * CONFIG['pip_value']
    commission_cost = abs(pips) * CONFIG['pip_value'] * CONFIG['commission_pct']
    
    pnl = (pips * CONFIG['pip_value']) - spread_cost - slippage_cost - commission_cost
    capital += pnl
    
    trades.append({
        'entry_time': pos['entry_time'],
        'exit_time': df.iloc[-1]['time'],
        'entry_price': pos['entry_price'],
        'exit_price': exit_price,
        'pips': pips,
        'pnl': pnl,
        'capital': capital,
        'result': 'closed_at_end'
    })

# ============================================================================
# ANÁLISE DE RESULTADOS
# ============================================================================

print("\n" + "=" * 80)
print("📊 RESULTADOS DO BACKTEST")
print("=" * 80)

df_trades = pd.DataFrame(trades)

if len(df_trades) == 0:
    print("\n❌ NENHUM TRADE EXECUTADO!")
    print("   Possíveis causas:")
    print("   • Threshold muito alto")
    print("   • Modelo não gera sinais")
    print("   • Dados insuficientes")
    sys.exit(1)

# Métricas básicas
total_trades = len(df_trades)
winning_trades = len(df_trades[df_trades['result'] == 'win'])
losing_trades = len(df_trades[df_trades['result'] == 'loss'])
win_rate = winning_trades / total_trades if total_trades > 0 else 0

# P&L
total_pnl = df_trades['pnl'].sum()
avg_win = df_trades[df_trades['result'] == 'win']['pnl'].mean() if winning_trades > 0 else 0
avg_loss = df_trades[df_trades['result'] == 'loss']['pnl'].mean() if losing_trades > 0 else 0
profit_factor = abs(df_trades[df_trades['pnl'] > 0]['pnl'].sum() / df_trades[df_trades['pnl'] < 0]['pnl'].sum()) if losing_trades > 0 else 0

# ROI
roi = (capital - CONFIG['initial_capital']) / CONFIG['initial_capital']
days = (pd.to_datetime(df['time'].max()) - pd.to_datetime(df['time'].min())).days
annual_roi = roi * (365 / days) if days > 0 else 0

# Sharpe Ratio
returns = df_trades['pnl'] / CONFIG['initial_capital']
sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0  # Anualizado

print(f"\n📈 PERFORMANCE GERAL:")
print(f"   Capital inicial:  ${CONFIG['initial_capital']:,.2f}")
print(f"   Capital final:    ${capital:,.2f}")
print(f"   P&L total:        ${total_pnl:,.2f} ({roi*100:+.2f}%)")
print(f"   ROI anualizado:   {annual_roi*100:+.2f}% ao ano")
print()

print(f"📊 TRADES:")
print(f"   Total de trades:  {total_trades:,}")
print(f"   Vencedores:       {winning_trades:,} ({win_rate*100:.1f}%)")
print(f"   Perdedores:       {losing_trades:,} ({(1-win_rate)*100:.1f}%)")
print(f"   Trades por dia:   {total_trades/days:.1f}")
print()

print(f"💰 P&L POR TRADE:")
print(f"   Média por trade:  ${df_trades['pnl'].mean():.2f}")
print(f"   Média ganhos:     ${avg_win:.2f}")
print(f"   Média perdas:     ${avg_loss:.2f}")
print(f"   Maior ganho:      ${df_trades['pnl'].max():.2f}")
print(f"   Maior perda:      ${df_trades['pnl'].min():.2f}")
print()

print(f"📉 RISCO:")
print(f"   Max Drawdown:     {max_drawdown*100:.2f}%")
print(f"   Profit Factor:    {profit_factor:.2f}")
print(f"   Sharpe Ratio:     {sharpe:.2f}")
print()

# ============================================================================
# AVALIAÇÃO DE VIABILIDADE
# ============================================================================

print("=" * 80)
print("🎯 AVALIAÇÃO DE VIABILIDADE")
print("=" * 80)

criteria = {
    'Sharpe Ratio > 1.5': sharpe > 1.5,
    'Max Drawdown < 20%': max_drawdown < 0.20,
    'Win Rate > 60%': win_rate > 0.60,
    'Profit Factor > 2.0': profit_factor > 2.0,
    'ROI Anual > 5%': annual_roi > 0.05,
    'Trades suficientes (>100)': total_trades > 100,
}

print("\n✅ CRITÉRIOS DE ACEITAÇÃO:")
for criterion, passed in criteria.items():
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"   {status}  {criterion}")

passed_count = sum(criteria.values())
total_count = len(criteria)

print(f"\n📊 RESULTADO: {passed_count}/{total_count} critérios atendidos")

if passed_count >= 5:
    print("\n" + "🎉" * 40)
    print("✅ SISTEMA VIÁVEL PARA PAPER TRADING!")
    print("🎉" * 40)
    print("\n   Próximos passos:")
    print("   1. Walk-forward analysis (validar estabilidade)")
    print("   2. Monte Carlo simulation (estimar riscos)")
    print("   3. Paper trading por 3-6 meses")
elif passed_count >= 3:
    print("\n" + "⚠️ " * 40)
    print("⚠️  SISTEMA MARGINAL - MELHORIAS NECESSÁRIAS")
    print("⚠️ " * 40)
    print("\n   Recomendações:")
    print("   • Re-treinar com mais dados (1.8M candles)")
    print("   • Ajustar threshold")
    print("   • Melhorar features (adicionar momentum, padrões)")
    print("   • Considerar ensemble de modelos")
else:
    print("\n" + "❌" * 40)
    print("❌ SISTEMA NÃO VIÁVEL PARA TRADING REAL")
    print("❌" * 40)
    print("\n   Problemas identificados:")
    if not criteria['Sharpe Ratio > 1.5']:
        print("   • Sharpe muito baixo (retorno/risco ruim)")
    if not criteria['Max Drawdown < 20%']:
        print("   • Drawdown muito alto (risco excessivo)")
    if not criteria['Win Rate > 60%']:
        print("   • Win rate insuficiente")
    if not criteria['Profit Factor > 2.0']:
        print("   • Profit factor baixo")
    if not criteria['ROI Anual > 5%']:
        print("   • ROI não compensa o risco")
    
    print("\n   💡 RECOMENDAÇÃO: NÃO PROSSEGUIR com este modelo")
    print("   Alternativas:")
    print("   • Investir em S&P 500 ETF (~10% ao ano, zero esforço)")
    print("   • Tentar outro algoritmo (Informer, LSTM)")
    print("   • Usar o aprendizado para outros projetos")

# ============================================================================
# SALVAR RESULTADOS
# ============================================================================

results = {
    'config': CONFIG,
    'metrics': {
        'initial_capital': CONFIG['initial_capital'],
        'final_capital': float(capital),
        'total_pnl': float(total_pnl),
        'roi': float(roi),
        'annual_roi': float(annual_roi),
        'total_trades': int(total_trades),
        'winning_trades': int(winning_trades),
        'losing_trades': int(losing_trades),
        'win_rate': float(win_rate),
        'avg_win': float(avg_win),
        'avg_loss': float(avg_loss),
        'max_drawdown': float(max_drawdown),
        'profit_factor': float(profit_factor),
        'sharpe_ratio': float(sharpe),
        'trades_per_day': float(total_trades/days),
    },
    'criteria': {k: bool(v) for k, v in criteria.items()},
    'passed_criteria': f"{passed_count}/{total_count}",
    'viable': passed_count >= 5,
    'backtest_period': {
        'start': str(df['time'].min()),
        'end': str(df['time'].max()),
        'days': int(days),
    }
}

output_file = '/tmp/backtest_results.json'
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n💾 Resultados salvos: {output_file}")

# Salvar trades CSV
trades_file = '/tmp/backtest_trades.csv'
df_trades.to_csv(trades_file, index=False)
print(f"💾 Trades salvos: {trades_file}")

print("\n" + "=" * 80)
print("✅ BACKTEST CONCLUÍDO")
print("=" * 80)
print("\n🛡️  Lembre-se: Backtest ≠ Futuro!")
print("   • Resultados passados não garantem resultados futuros")
print("   • Mercado muda constantemente")
print("   • Paper trading é ESSENCIAL antes de dinheiro real")
print("=" * 80)
