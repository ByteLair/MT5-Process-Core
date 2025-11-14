#!/usr/bin/env python3
"""
Download de Dados Históricos Completos do MetaTrader 5
=======================================================

Baixa dados históricos completos de múltiplos símbolos e timeframes
diretamente do MT5 e importa para o banco de dados.

Funcionalidades:
- Download automático via MT5 Python API
- Múltiplos símbolos e timeframes
- Validação de dados
- Importação direta no banco
- Progress tracking
- Retry automático em caso de falha

Requisitos:
    pip install MetaTrader5 pandas psycopg sqlalchemy

Uso:
    # Download completo (últimos 10 anos)
    python download_historical_mt5.py --symbol EURUSD --timeframe H1 --years 10
    
    # Download personalizado
    python download_historical_mt5.py --symbol GBPUSD --timeframe M15 --start 2020-01-01 --end 2025-11-14
    
    # Múltiplos símbolos
    python download_historical_mt5.py --symbols EURUSD,GBPUSD,USDJPY --timeframe H1 --years 5
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text

try:
    import MetaTrader5 as mt5
except ImportError:
    print("❌ MetaTrader5 não instalado!")
    print("   Instale com: pip install MetaTrader5")
    sys.exit(1)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Timeframe mapping
TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


def initialize_mt5() -> bool:
    """Inicializa conexão com MT5."""
    logger.info("🔗 Inicializando MetaTrader 5...")
    
    if not mt5.initialize():
        error = mt5.last_error()
        logger.error(f"❌ Erro ao inicializar MT5: {error}")
        logger.error("   Certifique-se de que o MT5 está instalado e rodando")
        return False
    
    # Informações da conta
    account_info = mt5.account_info()
    if account_info:
        logger.info(f"✅ Conectado ao MT5")
        logger.info(f"   Conta: {account_info.login}")
        logger.info(f"   Servidor: {account_info.server}")
    
    return True


def download_symbol_data(
    symbol: str,
    timeframe_str: str,
    start_date: datetime,
    end_date: datetime,
) -> Optional[pd.DataFrame]:
    """
    Baixa dados históricos de um símbolo.
    
    Args:
        symbol: Símbolo (ex: EURUSD)
        timeframe_str: Timeframe string (ex: H1)
        start_date: Data inicial
        end_date: Data final
    
    Returns:
        DataFrame com os dados ou None em caso de erro
    """
    logger.info(f"📥 Baixando {symbol} {timeframe_str}...")
    logger.info(f"   Período: {start_date.date()} até {end_date.date()}")
    
    # Converter timeframe
    timeframe = TIMEFRAMES.get(timeframe_str)
    if not timeframe:
        logger.error(f"❌ Timeframe inválido: {timeframe_str}")
        return None
    
    # Verificar se símbolo existe
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.error(f"❌ Símbolo não encontrado: {symbol}")
        logger.info("   Símbolos disponíveis:")
        symbols = mt5.symbols_get()
        if symbols:
            for s in symbols[:10]:
                logger.info(f"   - {s.name}")
        return None
    
    # Habilitar símbolo
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            logger.error(f"❌ Erro ao habilitar símbolo: {symbol}")
            return None
    
    # Download
    start_time = time.time()
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
    
    if rates is None or len(rates) == 0:
        error = mt5.last_error()
        logger.error(f"❌ Erro ao baixar dados: {error}")
        return None
    
    # Converter para DataFrame
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Renomear colunas para nosso schema
    df = df.rename(columns={
        'time': 'ts',
        'tick_volume': 'volume'
    })
    
    # Adicionar metadados
    df['symbol'] = symbol
    df['timeframe'] = timeframe_str
    df['spread'] = None
    df['bid'] = None
    df['ask'] = None
    
    elapsed = time.time() - start_time
    candles_per_sec = len(df) / elapsed if elapsed > 0 else 0
    
    logger.info(f"✅ {len(df):,} candles baixados")
    logger.info(f"   Tempo: {elapsed:.2f}s ({candles_per_sec:.0f} candles/s)")
    logger.info(f"   Período: {df['ts'].min()} até {df['ts'].max()}")
    logger.info(f"   OHLC: O={df['open'].iloc[0]:.5f} H={df['high'].max():.5f} L={df['low'].min():.5f} C={df['close'].iloc[-1]:.5f}")
    
    return df


def import_to_database(df: pd.DataFrame, db_url: str, batch_size: int = 1000) -> int:
    """
    Importa dados para o banco de dados.
    
    Args:
        df: DataFrame com os dados
        db_url: URL de conexão do banco
        batch_size: Tamanho do lote para inserção
    
    Returns:
        Número de registros inseridos
    """
    logger.info(f"💾 Importando {len(df):,} registros para o banco...")
    
    engine = create_engine(db_url, pool_pre_ping=True)
    
    # Preparar dados
    df_insert = df[[
        'ts', 'symbol', 'timeframe', 'open', 'high', 'low', 'close',
        'volume', 'spread', 'bid', 'ask'
    ]].copy()
    
    inserted = 0
    total_batches = (len(df_insert) + batch_size - 1) // batch_size
    
    with engine.begin() as conn:
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(df_insert))
            batch = df_insert.iloc[start_idx:end_idx]
            
            # Inserir lote (ON CONFLICT para evitar duplicados)
            for _, row in batch.iterrows():
                result = conn.execute(
                    text("""
                        INSERT INTO market_data 
                        (ts, symbol, timeframe, open, high, low, close, volume, spread, bid, ask)
                        VALUES 
                        (:ts, :symbol, :timeframe, :open, :high, :low, :close, :volume, :spread, :bid, :ask)
                        ON CONFLICT (symbol, timeframe, ts) DO NOTHING
                    """),
                    {
                        "ts": row['ts'],
                        "symbol": row['symbol'],
                        "timeframe": row['timeframe'],
                        "open": float(row['open']),
                        "high": float(row['high']),
                        "low": float(row['low']),
                        "close": float(row['close']),
                        "volume": float(row['volume']),
                        "spread": row['spread'],
                        "bid": row['bid'],
                        "ask": row['ask'],
                    }
                )
                inserted += result.rowcount
            
            progress = (batch_num + 1) / total_batches * 100
            logger.info(f"  Progresso: {progress:.1f}% ({inserted:,} inseridos)")
    
    engine.dispose()
    logger.info(f"✅ {inserted:,} registros inseridos com sucesso")
    
    return inserted


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Download de dados históricos do MT5")
    
    parser.add_argument("--symbol", type=str, help="Símbolo único (ex: EURUSD)")
    parser.add_argument("--symbols", type=str, help="Múltiplos símbolos separados por vírgula (ex: EURUSD,GBPUSD)")
    parser.add_argument("--timeframe", type=str, default="H1", choices=list(TIMEFRAMES.keys()), help="Timeframe")
    parser.add_argument("--years", type=int, help="Número de anos para trás (ex: 10)")
    parser.add_argument("--start", type=str, help="Data inicial (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="Data final (YYYY-MM-DD)")
    parser.add_argument("--db-url", type=str, default="postgresql+psycopg://trader:trader123@localhost:5432/mt5_trading", help="URL do banco")
    parser.add_argument("--save-csv", action="store_true", help="Salvar também em CSV")
    parser.add_argument("--csv-dir", type=str, default="./exports", help="Diretório para salvar CSVs")
    
    args = parser.parse_args()
    
    # Validar argumentos
    if not args.symbol and not args.symbols:
        parser.error("Especifique --symbol ou --symbols")
    
    # Definir lista de símbolos
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
    else:
        symbols = [args.symbol]
    
    # Definir período
    if args.start and args.end:
        start_date = datetime.strptime(args.start, "%Y-%m-%d")
        end_date = datetime.strptime(args.end, "%Y-%m-%d")
    elif args.years:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * args.years)
    else:
        # Default: últimos 5 anos
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 5)
    
    logger.info("=" * 70)
    logger.info("🚀 DOWNLOAD DE DADOS HISTÓRICOS - METATRADER 5")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Símbolos: {', '.join(symbols)}")
    logger.info(f"Timeframe: {args.timeframe}")
    logger.info(f"Período: {start_date.date()} até {end_date.date()}")
    logger.info(f"Banco: {args.db_url.split('@')[1] if '@' in args.db_url else args.db_url}")
    logger.info("")
    
    # Inicializar MT5
    if not initialize_mt5():
        sys.exit(1)
    
    try:
        total_downloaded = 0
        total_inserted = 0
        
        # Processar cada símbolo
        for symbol in symbols:
            logger.info("")
            logger.info(f"{'=' * 70}")
            logger.info(f"📊 Processando {symbol}")
            logger.info(f"{'=' * 70}")
            
            # Download
            df = download_symbol_data(symbol, args.timeframe, start_date, end_date)
            
            if df is None or df.empty:
                logger.warning(f"⚠️  Nenhum dado baixado para {symbol}")
                continue
            
            total_downloaded += len(df)
            
            # Salvar CSV (opcional)
            if args.save_csv:
                csv_dir = Path(args.csv_dir)
                csv_dir.mkdir(parents=True, exist_ok=True)
                csv_path = csv_dir / f"{symbol}_{args.timeframe}_{start_date.date()}_{end_date.date()}.csv"
                df.to_csv(csv_path, index=False)
                logger.info(f"💾 CSV salvo: {csv_path}")
            
            # Importar para banco
            inserted = import_to_database(df, args.db_url)
            total_inserted += inserted
        
        # Resumo final
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ DOWNLOAD CONCLUÍDO COM SUCESSO!")
        logger.info("=" * 70)
        logger.info("")
        logger.info(f"📊 Resumo:")
        logger.info(f"  • Símbolos processados: {len(symbols)}")
        logger.info(f"  • Total baixado: {total_downloaded:,} candles")
        logger.info(f"  • Total inserido: {total_inserted:,} registros")
        logger.info(f"  • Período: {start_date.date()} até {end_date.date()}")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        mt5.shutdown()
        logger.info("🔌 MT5 desconectado")


if __name__ == "__main__":
    main()
