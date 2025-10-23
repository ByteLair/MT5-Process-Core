# =============================================================
# Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
# All rights reserved. | Todos os direitos reservados.
# Private License: This code is the exclusive property of Felipe Petracco Carmo.
# Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
# Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
# Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
# =============================================================

"""
Endpoint de status e monitoramento do fluxo de dados.

Fornece métricas sobre ingestão, agregação e saúde do sistema.
"""

from datetime import datetime, timezone
import os

from fastapi import APIRouter
from sqlalchemy import text

DISABLE_TICK_INGEST = os.getenv("DISABLE_TICK_INGEST", "true").lower() in {"1", "true", "yes"}

try:
    from ..db import engine as ENGINE
except Exception:
    try:
        from db import engine as ENGINE
    except Exception:
        import os

        from sqlalchemy import create_engine

        DATABASE_URL = os.getenv(
            "DATABASE_URL", "postgresql+psycopg://trader:trader123@db:5432/mt5_trading"
        )
        ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)

router = APIRouter(prefix="/status", tags=["monitoring"])


@router.get("/data-flow")
def data_flow_status():
    """
    Retorna status detalhado do fluxo de dados.

    Útil para monitoramento e diagnóstico de problemas de ingestão.
    """
    try:
        with ENGINE.connect() as conn:
            # Dados brutos
            raw_stats = conn.execute(
                text(
                    """
                SELECT 
                    COUNT(*) as total_records,
                    MIN(received_at) as first_received,
                    MAX(received_at) as last_received,
                    EXTRACT(EPOCH FROM (NOW() - MAX(received_at)))/60 as minutes_since_last
                FROM public.market_data_raw
                """
                )
            ).fetchone()

            # Dados agregados
            agg_stats = conn.execute(
                text(
                    """
                SELECT 
                    COUNT(*) as total_candles,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    MIN(ts) as first_candle,
                    MAX(ts) as last_candle,
                    EXTRACT(EPOCH FROM (NOW() - MAX(ts)))/60 as minutes_since_last
                FROM public.market_data
                """
                )
            ).fetchone()

            # Estado do agregador
            agg_state = conn.execute(
                text(
                    """
                SELECT value as last_processed
                FROM public.aggregator_state
                WHERE key = 'tick_agg_last_received_at'
                """
                )
            ).fetchone()

            # Símbolos por timeframe
            symbols_by_tf = conn.execute(
                text(
                    """
                SELECT 
                    timeframe,
                    COUNT(DISTINCT symbol) as symbols,
                    MAX(ts) as latest_data
                FROM public.market_data
                GROUP BY timeframe
                ORDER BY timeframe
                """
                )
            ).fetchall()

            # Health check: detecta problemas
            health_issues = []
            now = datetime.now(timezone.utc)

            if not DISABLE_TICK_INGEST:
                if raw_stats and raw_stats[0] == 0:
                    health_issues.append({
                        "severity": "critical",
                        "issue": "no_raw_data",
                        "message": "Nenhum dado bruto recebido. EA pode estar offline.",
                    })
                elif raw_stats and raw_stats[3] and raw_stats[3] > 10:
                    health_issues.append({
                        "severity": "warning",
                        "issue": "stale_raw_data",
                        "message": f"Último dado bruto há {raw_stats[3]:.1f} minutos. EA pode estar offline.",
                    })

            if agg_stats and agg_stats[0] == 0:
                health_issues.append({
                    "severity": "critical",
                    "issue": "no_aggregated_data",
                    "message": "Nenhum dado agregado. Tick aggregator pode estar com problema.",
                })
            elif agg_stats and agg_stats[4] and agg_stats[4] > 15:
                health_issues.append({
                    "severity": "warning",
                    "issue": "stale_aggregated_data",
                    "message": f"Último candle há {agg_stats[4]:.1f} minutos. Verifique agregador.",
                })

            # Status geral
            if not health_issues:
                overall_status = "healthy"
            elif any(issue["severity"] == "critical" for issue in health_issues):
                overall_status = "critical"
            else:
                overall_status = "degraded"

            return {
                "status": overall_status,
                "timestamp": now.isoformat(),
                "raw_data": {
                    "total_records": raw_stats[0] if raw_stats else 0,
                    "first_received": raw_stats[1].isoformat() if raw_stats and raw_stats[1] else None,
                    "last_received": raw_stats[2].isoformat() if raw_stats and raw_stats[2] else None,
                    "minutes_since_last": round(raw_stats[3], 2) if raw_stats and raw_stats[3] else None,
                },
                "aggregated_data": {
                    "total_candles": agg_stats[0] if agg_stats else 0,
                    "unique_symbols": agg_stats[1] if agg_stats else 0,
                    "first_candle": agg_stats[2].isoformat() if agg_stats and agg_stats[2] else None,
                    "last_candle": agg_stats[3].isoformat() if agg_stats and agg_stats[3] else None,
                    "minutes_since_last": round(agg_stats[4], 2) if agg_stats and agg_stats[4] else None,
                },
                "aggregator_state": {
                    "last_processed": agg_state[0] if agg_state else None,
                },
                "symbols_by_timeframe": [
                    {
                        "timeframe": row[0],
                        "symbols": row[1],
                        "latest_data": row[2].isoformat() if row[2] else None,
                    }
                    for row in symbols_by_tf
                ],
                "health_issues": health_issues,
            }

    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


@router.get("/db-connection")
def database_connection_status():
    """Verifica conectividade com o banco de dados."""
    try:
        with ENGINE.connect() as conn:
            result = conn.execute(text("SELECT 1 as test, NOW() as server_time")).fetchone()
            return {
                "status": "connected",
                "test_query": result[0],
                "server_time": result[1].isoformat(),
                "pool_size": ENGINE.pool.size(),
                "pool_checked_out": ENGINE.pool.checkedout(),
            }
    except Exception as e:
        return {
            "status": "disconnected",
            "error": str(e),
        }


@router.get("/recent-activity")
def recent_activity(limit: int = 10):
    """
    Retorna atividade recente de ingestão.

    Args:
        limit: Número de registros a retornar (default: 10)
    """
    try:
        with ENGINE.connect() as conn:
            recent_raw = conn.execute(
                text(
                    """
                SELECT 
                    received_at,
                    source,
                    jsonb_array_length(payload->'ticks') as num_ticks,
                    payload->'ticks'->0->>'symbol' as sample_symbol
                FROM public.market_data_raw
                ORDER BY received_at DESC
                LIMIT :limit
                """
                ),
                {"limit": limit},
            ).fetchall()

            recent_candles = conn.execute(
                text(
                    """
                SELECT 
                    ts,
                    symbol,
                    timeframe,
                    close,
                    volume
                FROM public.market_data
                ORDER BY ts DESC
                LIMIT :limit
                """
                ),
                {"limit": limit},
            ).fetchall()

            return {
                "recent_raw_ingestion": [
                    {
                        "received_at": row[0].isoformat(),
                        "source": row[1],
                        "num_ticks": row[2],
                        "sample_symbol": row[3],
                    }
                    for row in recent_raw
                ],
                "recent_candles": [
                    {
                        "timestamp": row[0].isoformat(),
                        "symbol": row[1],
                        "timeframe": row[2],
                        "close": float(row[3]) if row[3] else None,
                        "volume": float(row[4]) if row[4] else None,
                    }
                    for row in recent_candles
                ],
            }
    except Exception as e:
        return {
            "error": str(e),
        }
