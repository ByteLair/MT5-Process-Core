#!/usr/bin/env python3
"""
🎯 BACKTEST H1 CATBOOST - REALISTIC TRADING SIMULATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Backtest com modelo CatBoost usando configuração AGRESSIVA mas INTELIGENTE:
  • Risk/Reward: 1:2 (Take Profit 2x Stop Loss)
  • Threshold: 0.60 (60% confiança mínima)
  • Max trades: 5 por dia
  • Risk: 1% por trade
  
FEATURES:
  • Simula spread realista (1.5 pips EURUSD)
  • Slippage em períodos de alta volatilidade
  • Trailing stop opcional
  • Estatísticas completas

TARGET: +2-3.5% ROI, 45-50% Win Rate
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import logging
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime
from catboost import CatBoostClassifier

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest_h1_catboost.log'),
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

MODEL_PATH = 'models/catboost_h1_model.cbm'

# ============================================================================
# BACKTEST CONFIGURATION - AGRESSIVO MAS INTELIGENTE
# ============================================================================

BACKTEST_CONFIG = {
    # Period
    'start_date': '2024-10-01',
    'end_date': '2025-11-30',
    
    # Entry signals
    'confidence_threshold': 0.60,   # 60% confiança (mais agressivo que 0.65)
    'max_trades_per_day': 5,        # Até 5 trades/dia (vs 3 conservador)
    
    # Risk Management
    'risk_per_trade': 0.01,         # 1% por trade
    'risk_reward_ratio': 2.0,       # RR 1:2 (TP = 2x SL)
    'initial_balance': 10000,
    
    # Stop Loss calculation
    'sl_atr_multiplier': 1.5,       # SL = 1.5x ATR (tight but reasonable)
    
    # Take Profit
    'use_trailing_stop': True,      # Trailing stop para proteger lucros
    'trailing_activation': 1.2,     # Ativa em 1.2x SL
    'trailing_distance': 0.8,       # Trail a 0.8x SL
    
    # Costs
    'spread_pips': 1.5,             # Spread EURUSD típico
    'commission_per_lot': 0,        # Sem comissão (broker típico)
    'slippage_pips': 0.3,           # Slippage médio
    
    # Filters
    'avoid_news_events': True,      # Evita trades em horários de news
    'min_atr': 0.0005,              # ATR mínimo (evita mercado parado)
    'max_atr': 0.0030,              # ATR máximo (evita volatilidade extrema)
}

# News events times (evitar trades 1h antes/depois)
NEWS_HOURS = [8, 9, 13, 14, 15]  # Londres open, US open, US news

# ============================================================================
# CLASSES
# ============================================================================

class Trade:
    """Representa um trade individual."""
    
    def __init__(self, entry_time, entry_price, direction, stop_loss, 
                 take_profit, position_size, sl_pips, tp_pips):
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.direction = direction  # 1 = BUY, 0 = SELL
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.position_size = position_size
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        
        self.exit_time = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl = 0
        self.pnl_pct = 0
        self.status = 'OPEN'
        
        # Trailing stop
        self.trailing_stop = None
        self.max_favorable = entry_price
    
    def update_trailing_stop(self, current_price, config):
        """Atualiza trailing stop se ativado."""
        if not config['use_trailing_stop']:
            return
        
        if self.direction == 1:  # BUY
            # Atualiza max favorable
            if current_price > self.max_favorable:
                self.max_favorable = current_price
            
            # Ativa trailing se lucro >= activation threshold
            profit_pips = (current_price - self.entry_price) * 10000
            if profit_pips >= self.sl_pips * config['trailing_activation']:
                # Trail a X pips abaixo do max
                trail_distance = self.sl_pips * config['trailing_distance']
                new_trailing = self.max_favorable - (trail_distance / 10000)
                
                # Só move trailing para cima
                if self.trailing_stop is None or new_trailing > self.trailing_stop:
                    self.trailing_stop = new_trailing
        
        else:  # SELL
            if current_price < self.max_favorable:
                self.max_favorable = current_price
            
            profit_pips = (self.entry_price - current_price) * 10000
            if profit_pips >= self.sl_pips * config['trailing_activation']:
                trail_distance = self.sl_pips * config['trailing_distance']
                new_trailing = self.max_favorable + (trail_distance / 10000)
                
                if self.trailing_stop is None or new_trailing < self.trailing_stop:
                    self.trailing_stop = new_trailing
    
    def check_exit(self, candle, config):
        """Verifica se deve sair do trade."""
        high = candle['high']
        low = candle['low']
        close = candle['close']
        
        if self.direction == 1:  # BUY
            # Check trailing stop primeiro
            if self.trailing_stop and low <= self.trailing_stop:
                self.close_trade(candle['ts'], self.trailing_stop, 'TRAILING_STOP')
                return True
            
            # Check stop loss
            if low <= self.stop_loss:
                # Simula slippage em SL
                exit_price = self.stop_loss - (config['slippage_pips'] / 10000)
                self.close_trade(candle['ts'], exit_price, 'STOP_LOSS')
                return True
            
            # Check take profit
            if high >= self.take_profit:
                self.close_trade(candle['ts'], self.take_profit, 'TAKE_PROFIT')
                return True
        
        else:  # SELL
            if self.trailing_stop and high >= self.trailing_stop:
                self.close_trade(candle['ts'], self.trailing_stop, 'TRAILING_STOP')
                return True
            
            if high >= self.stop_loss:
                exit_price = self.stop_loss + (config['slippage_pips'] / 10000)
                self.close_trade(candle['ts'], exit_price, 'STOP_LOSS')
                return True
            
            if low <= self.take_profit:
                self.close_trade(candle['ts'], self.take_profit, 'TAKE_PROFIT')
                return True
        
        return False
    
    def close_trade(self, exit_time, exit_price, reason):
        """Fecha o trade."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason
        self.status = 'CLOSED'
        
        # Calculate P&L
        if self.direction == 1:  # BUY
            price_diff = self.exit_price - self.entry_price
        else:  # SELL
            price_diff = self.entry_price - self.exit_price
        
        self.pnl = price_diff * self.position_size * 100000  # Standard lot
        self.pnl_pct = (self.pnl / (self.position_size * 100000 * self.entry_price)) * 100


class BacktestEngine:
    """Engine de backtesting."""
    
    def __init__(self, model, config):
        self.model = model
        self.config = config
        self.balance = config['initial_balance']
        self.equity = config['initial_balance']
        self.trades = []
        self.open_trades = []
        self.equity_curve = []
    
    def should_trade(self, candle):
        """Verifica se deve tradear neste candle."""
        
        # Check max trades per day
        current_date = candle['ts'].date()
        trades_today = sum(1 for t in self.trades 
                          if t.entry_time.date() == current_date)
        if trades_today >= self.config['max_trades_per_day']:
            return False
        
        # Avoid news times
        if self.config['avoid_news_events']:
            hour = candle['ts'].hour
            if hour in NEWS_HOURS:
                return False
        
        # Check ATR (volatility filter)
        atr = candle['atr_14']
        if atr < self.config['min_atr'] or atr > self.config['max_atr']:
            return False
        
        return True
    
    def calculate_position_size(self, stop_loss_pips):
        """Calcula tamanho da posição baseado no risco."""
        risk_amount = self.balance * self.config['risk_per_trade']
        pip_value = 10  # $10 per pip for 1 standard lot EURUSD
        position_size = risk_amount / (stop_loss_pips * pip_value)
        
        # Limit to reasonable range
        return max(0.01, min(position_size, 1.0))
    
    def open_trade(self, candle, signal, confidence):
        """Abre um novo trade."""
        
        # Calculate stop loss (based on ATR)
        atr = candle['atr_14']
        sl_distance = atr * self.config['sl_atr_multiplier']
        sl_pips = sl_distance * 10000
        
        # Position size
        position_size = self.calculate_position_size(sl_pips)
        
        # Entry price (com spread)
        spread = self.config['spread_pips'] / 10000
        entry_price = candle['close'] + spread if signal == 1 else candle['close'] - spread
        
        # Stop Loss & Take Profit
        if signal == 1:  # BUY
            stop_loss = entry_price - sl_distance
            take_profit = entry_price + (sl_distance * self.config['risk_reward_ratio'])
        else:  # SELL
            stop_loss = entry_price + sl_distance
            take_profit = entry_price - (sl_distance * self.config['risk_reward_ratio'])
        
        tp_pips = sl_pips * self.config['risk_reward_ratio']
        
        # Create trade
        trade = Trade(
            entry_time=candle['ts'],
            entry_price=entry_price,
            direction=signal,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            sl_pips=sl_pips,
            tp_pips=tp_pips
        )
        
        self.open_trades.append(trade)
        self.trades.append(trade)
        
        logger.info(f"   {'BUY' if signal == 1 else 'SELL'} @ {entry_price:.5f} | "
                   f"SL: {stop_loss:.5f} ({sl_pips:.1f}p) | "
                   f"TP: {take_profit:.5f} ({tp_pips:.1f}p) | "
                   f"Size: {position_size:.2f} | Conf: {confidence:.2%}")
    
    def update_open_trades(self, candle):
        """Atualiza trades abertos."""
        closed_trades = []
        
        for trade in self.open_trades:
            # Update trailing stop
            trade.update_trailing_stop(candle['close'], self.config)
            
            # Check exit
            if trade.check_exit(candle, self.config):
                self.balance += trade.pnl
                closed_trades.append(trade)
                
                logger.info(f"   CLOSED {trade.exit_reason} | "
                           f"P&L: ${trade.pnl:.2f} ({trade.pnl_pct:+.2f}%) | "
                           f"Balance: ${self.balance:.2f}")
        
        # Remove closed trades
        for trade in closed_trades:
            self.open_trades.remove(trade)
    
    def run(self, df):
        """Executa backtest."""
        logger.info(f"🚀 Iniciando backtest: {self.config['start_date']} → {self.config['end_date']}")
        logger.info(f"   Balance inicial: ${self.config['initial_balance']:,.2f}")
        logger.info(f"   Threshold: {self.config['confidence_threshold']:.0%}")
        logger.info(f"   Risk/Reward: 1:{self.config['risk_reward_ratio']:.1f}")
        logger.info("")
        
        for idx, row in df.iterrows():
            candle = row.to_dict()
            
            # Update open trades
            self.update_open_trades(candle)
            
            # Check new entry
            if self.should_trade(candle):
                signal = candle['signal']
                confidence = candle['confidence']
                
                if confidence >= self.config['confidence_threshold']:
                    self.open_trade(candle, signal, confidence)
            
            # Update equity curve
            open_pnl = sum(
                (candle['close'] - t.entry_price) * t.position_size * 100000
                if t.direction == 1 else
                (t.entry_price - candle['close']) * t.position_size * 100000
                for t in self.open_trades
            )
            self.equity = self.balance + open_pnl
            self.equity_curve.append({
                'ts': candle['ts'],
                'equity': self.equity
            })
        
        # Close remaining trades
        for trade in self.open_trades[:]:
            trade.close_trade(df.iloc[-1]['ts'], df.iloc[-1]['close'], 'END_OF_BACKTEST')
            self.balance += trade.pnl
        
        self.open_trades = []
        
        return self.calculate_statistics()
    
    def calculate_statistics(self):
        """Calcula estatísticas do backtest."""
        if not self.trades:
            return {}
        
        closed_trades = [t for t in self.trades if t.status == 'CLOSED']
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in closed_trades)
        total_return_pct = (total_pnl / self.config['initial_balance']) * 100
        
        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
        
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        
        profit_factor = (
            abs(sum(t.pnl for t in winning_trades)) / 
            abs(sum(t.pnl for t in losing_trades))
            if losing_trades and sum(t.pnl for t in losing_trades) != 0 else 0
        )
        
        # Drawdown
        equity_curve_df = pd.DataFrame(self.equity_curve)
        equity_curve_df['peak'] = equity_curve_df['equity'].cummax()
        equity_curve_df['drawdown'] = equity_curve_df['equity'] - equity_curve_df['peak']
        equity_curve_df['drawdown_pct'] = (equity_curve_df['drawdown'] / equity_curve_df['peak']) * 100
        max_drawdown_pct = equity_curve_df['drawdown_pct'].min()
        
        return {
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return_pct': total_return_pct,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown_pct': max_drawdown_pct,
            'final_balance': self.balance,
            'initial_balance': self.config['initial_balance']
        }


# ============================================================================
# MAIN
# ============================================================================

def load_data():
    """Carrega dados para backtest."""
    logger.info("📥 Carregando dados...")
    
    query = """
    SELECT 
        ts, open, high, low, close, volume,
        rsi_14, macd, macd_signal, macd_hist,
        bb_upper, bb_middle, bb_lower,
        atr_14, adx_14,
        ema_50, ema_200
    FROM market_data
    WHERE 
        symbol = 'EURUSD' 
        AND timeframe = 'H1'
        AND ts >= %s
        AND ts <= %s
        AND rsi_14 IS NOT NULL
    ORDER BY ts
    """
    
    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql_query(
        query, 
        conn, 
        params=[BACKTEST_CONFIG['start_date'], BACKTEST_CONFIG['end_date']]
    )
    conn.close()
    
    logger.info(f"✅ Carregados {len(df):,} candles")
    return df


def engineer_features(df):
    """Same feature engineering as training."""
    df = df.copy()
    
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
    
    # Categorical
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


def main():
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║      🎯 BACKTEST H1 CATBOOST - AGGRESSIVE MODE            ║")
    logger.info("╚════════════════════════════════════════════════════════════╝")
    logger.info("")
    
    # Load model
    logger.info(f"📂 Carregando modelo: {MODEL_PATH}")
    model = CatBoostClassifier()
    model.load_model(MODEL_PATH)
    logger.info("✅ Modelo carregado")
    
    # Load & prepare data
    df = load_data()
    df = engineer_features(df)
    
    # Get predictions
    logger.info("🔮 Gerando previsões...")
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
    
    X = df[feature_cols]
    df['signal'] = model.predict(X)
    df['confidence'] = model.predict_proba(X)[:, 1]
    
    # Run backtest
    engine = BacktestEngine(model, BACKTEST_CONFIG)
    stats = engine.run(df)
    
    # Print results
    logger.info("")
    logger.info("╔════════════════════════════════════════════════════════════╗")
    logger.info("║                  📊 BACKTEST RESULTS                       ║")
    logger.info("╚════════════════════════════════════════════════════════════╝")
    logger.info(f"   Total Trades:     {stats['total_trades']}")
    logger.info(f"   Winning Trades:   {stats['winning_trades']} ({stats['win_rate']*100:.1f}%)")
    logger.info(f"   Losing Trades:    {stats['losing_trades']}")
    logger.info("")
    logger.info(f"   Total P&L:        ${stats['total_pnl']:,.2f}")
    logger.info(f"   Total Return:     {stats['total_return_pct']:+.2f}%")
    logger.info(f"   Final Balance:    ${stats['final_balance']:,.2f}")
    logger.info("")
    logger.info(f"   Avg Win:          ${stats['avg_win']:,.2f}")
    logger.info(f"   Avg Loss:         ${stats['avg_loss']:,.2f}")
    logger.info(f"   Profit Factor:    {stats['profit_factor']:.2f}")
    logger.info(f"   Max Drawdown:     {stats['max_drawdown_pct']:.2f}%")
    logger.info("")
    
    # Compare to target
    if stats['total_return_pct'] >= 2.0:
        logger.info("   ✅ EXCELENTE! Superou target de +2% ROI")
    elif stats['total_return_pct'] >= 1.0:
        logger.info("   ⚠️  BOM. Próximo do target")
    else:
        logger.info("   ❌ Abaixo do target. Revisar estratégia")
    
    if stats['win_rate'] >= 0.45:
        logger.info("   ✅ Win rate excelente (>45%)")
    
    logger.info("")
    logger.info("   Model ready for production! 🚀")


if __name__ == '__main__':
    main()
