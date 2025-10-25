# api/app/ea_signals.py
"""
EA Signals Router
Endpoints for managing AI signals to be sent to the EA
"""
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

import joblib
import pandas as pd
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import engine
from app.ea_communicator import get_ea_communicator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ea", tags=["ea-signals"])

API_KEY = os.getenv("API_KEY", "mt5_trading_secure_key_2025_prod")
MODEL_PATH = os.environ.get("MODEL_PATH", "/models/rf_m1.pkl")


def auth(x_api_key: str | None):
    """Validate API key"""
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")


class GenerateSignalRequest(BaseModel):
    """Request to generate trading signal"""
    symbol: str
    timeframe: str = "M1"
    force: bool = False  # Force signal generation even if confidence is low


class PushSignalsResponse(BaseModel):
    """Response from push signals endpoint"""
    success: bool
    sent_count: int
    message: str


@router.post("/generate-signal", response_model=dict)
async def generate_signal(
    request: GenerateSignalRequest,
    x_api_key: str | None = Header(None)
):
    """
    Generate a trading signal from AI model and add to queue
    
    This endpoint:
    1. Loads the latest market data for the symbol
    2. Runs AI prediction
    3. Generates a trading signal if confidence is high enough
    4. Adds signal to the queue to be sent to EA
    """
    auth(x_api_key)
    
    try:
        # Load model
        model_data = joblib.load(MODEL_PATH)
        model = model_data.get("model") if isinstance(model_data, dict) else model_data
        features = model_data.get("features", [
            "close", "volume", "spread", "rsi", "macd", "macd_signal",
            "macd_hist", "atr", "ma60", "ret_1"
        ]) if isinstance(model_data, dict) else [
            "close", "volume", "spread", "rsi", "macd", "macd_signal",
            "macd_hist", "atr", "ma60", "ret_1"
        ]
        
        # Get latest features from database
        with engine.connect() as conn:
            # Try to get from features table first
            df = pd.read_sql(
                text("""
                    SELECT ts, symbol, timeframe, close, volume, 
                           spread, rsi, macd, macd_signal, macd_hist,
                           atr, ma60, ret_1
                    FROM public.features_m1
                    WHERE symbol = :symbol
                    ORDER BY ts DESC
                    LIMIT 1
                """),
                conn,
                params={"symbol": request.symbol}
            )
            
            if df.empty:
                return {
                    "success": False,
                    "message": f"No data available for {request.symbol}",
                    "signal": None
                }
            
            # Prepare features for prediction
            X = df[features].fillna(0)
            
            # Get prediction
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(X)[0]
                confidence = float(proba[1])  # Probability of positive class
                label = int(confidence >= 0.55)  # Threshold
            else:
                pred = model.predict(X)[0]
                confidence = float(abs(pred))
                label = int(pred > 0)
            
            # Determine trading side based on prediction
            threshold = 0.55
            if confidence >= threshold:
                side = "BUY"
            elif confidence <= (1 - threshold):
                side = "SELL"
                confidence = 1 - confidence
            else:
                if not request.force:
                    return {
                        "success": True,
                        "message": f"Confidence too low ({confidence:.2%}), no signal generated",
                        "signal": None,
                        "confidence": confidence
                    }
                side = "NONE"
            
            # Calculate stop loss and take profit (simple example)
            if side in ["BUY", "SELL"]:
                sl_pips = 20
                tp_pips = 40
            else:
                sl_pips = 0
                tp_pips = 0
            
            # Create signal
            signal_id = str(uuid.uuid4())
            ts_now = datetime.now(timezone.utc)
            
            # Insert into signals queue
            with engine.begin() as insert_conn:
                insert_conn.execute(
                    text("""
                        INSERT INTO public.signals_queue
                        (id, ts, symbol, timeframe, side, confidence, sl_pips, tp_pips, status, meta)
                        VALUES (:id, :ts, :symbol, :timeframe, :side, :confidence, 
                                :sl_pips, :tp_pips, 'PENDING', :meta)
                    """),
                    {
                        "id": signal_id,
                        "ts": ts_now,
                        "symbol": request.symbol,
                        "timeframe": request.timeframe,
                        "side": side,
                        "confidence": confidence,
                        "sl_pips": sl_pips,
                        "tp_pips": tp_pips,
                        "meta": {
                            "model": "rf_m1",
                            "label": label,
                            "generated_at": ts_now.isoformat()
                        }
                    }
                )
            
            signal_data = {
                "signal_id": signal_id,
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "side": side,
                "confidence": confidence,
                "sl_pips": sl_pips,
                "tp_pips": tp_pips,
                "timestamp": ts_now.isoformat()
            }
            
            logger.info(f"Generated signal: {request.symbol} {side} (confidence: {confidence:.2%})")
            
            return {
                "success": True,
                "message": "Signal generated and added to queue",
                "signal": signal_data
            }
            
    except FileNotFoundError:
        logger.error(f"Model not found at {MODEL_PATH}")
        raise HTTPException(status_code=500, detail="ML model not found - please train the model first")
    except Exception as e:
        logger.error(f"Error generating signal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating signal: {str(e)}")


@router.post("/push-signals", response_model=PushSignalsResponse)
async def push_signals(x_api_key: str | None = Header(None)):
    """
    Manually trigger pushing all pending signals to EA
    
    This will immediately push all pending signals in the queue to the EA server.
    Normally this happens automatically via the background worker.
    """
    auth(x_api_key)
    
    try:
        ea_comm = get_ea_communicator()
        sent_count = await ea_comm.push_pending_signals()
        
        return PushSignalsResponse(
            success=True,
            sent_count=sent_count,
            message=f"Successfully pushed {sent_count} signals to EA"
        )
        
    except Exception as e:
        logger.error(f"Error pushing signals: {e}", exc_info=True)
        return PushSignalsResponse(
            success=False,
            sent_count=0,
            message=f"Error: {str(e)}"
        )


@router.get("/test-connection")
async def test_ea_connection(x_api_key: str | None = Header(None)):
    """
    Test connection to EA server
    
    Returns connection status and configuration
    """
    auth(x_api_key)
    
    ea_comm = get_ea_communicator()
    is_connected = await ea_comm.test_connection()
    
    return {
        "connected": is_connected,
        "ea_server": f"{os.getenv('EA_SERVER_IP', '192.168.15.18')}:{os.getenv('EA_SERVER_PORT', '8080')}",
        "ea_url": ea_comm.ea_url,
        "message": "✅ Connected" if is_connected else "❌ Connection failed"
    }


@router.get("/queue-status")
async def get_queue_status(x_api_key: str | None = Header(None)):
    """
    Get status of signals queue
    
    Returns counts of signals in different states
    """
    auth(x_api_key)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        status,
                        COUNT(*) as count,
                        MAX(ts) as latest_ts
                    FROM public.signals_queue
                    WHERE ts >= now() - interval '24 hours'
                    GROUP BY status
                """)
            )
            
            status_counts = {}
            for row in result:
                status_counts[row[0]] = {
                    "count": row[1],
                    "latest": row[2].isoformat() if row[2] else None
                }
            
            return {
                "success": True,
                "queue_status": status_counts,
                "period": "last_24_hours"
            }
            
    except Exception as e:
        logger.error(f"Error getting queue status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
