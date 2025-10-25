"""
EA Communicator Service
Sends AI trading decisions to the Expert Advisor server
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

import httpx
from sqlalchemy import text

from db import engine

logger = logging.getLogger(__name__)

# Configuration
EA_SERVER_IP = os.getenv("EA_SERVER_IP", "192.168.15.18")
EA_SERVER_PORT = os.getenv("EA_SERVER_PORT", "8080")
EA_SERVER_URL = f"http://{EA_SERVER_IP}:{EA_SERVER_PORT}/signals"
EA_API_KEY = os.getenv("EA_API_KEY", "mt5_trading_secure_key_2025_prod")
REQUEST_TIMEOUT = int(os.getenv("EA_REQUEST_TIMEOUT", "10"))


class EACommunicator:
    """Communicates trading signals to the Expert Advisor"""
    
    def __init__(self):
        self.ea_url = EA_SERVER_URL
        self.api_key = EA_API_KEY
        self.timeout = REQUEST_TIMEOUT
        
    async def send_signal(self, signal: Dict) -> bool:
        """
        Send a trading signal to the EA server
        
        Args:
            signal: Dictionary containing signal data with keys:
                - symbol: Trading symbol (e.g., "EURUSD")
                - timeframe: Timeframe (e.g., "M1")
                - side: Trade direction ("BUY", "SELL", "CLOSE", "NONE")
                - confidence: Confidence level (0.0-1.0)
                - sl_pips: Stop loss in pips
                - tp_pips: Take profit in pips
                - price: Current price (optional)
                - timestamp: Signal timestamp
                
        Returns:
            bool: True if signal was sent successfully, False otherwise
        """
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }
        
        payload = {
            "signal_id": signal.get("id", ""),
            "timestamp": signal.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "symbol": signal["symbol"],
            "timeframe": signal["timeframe"],
            "side": signal["side"],
            "confidence": signal.get("confidence", 0.0),
            "sl_pips": signal.get("sl_pips", 0),
            "tp_pips": signal.get("tp_pips", 0),
            "price": signal.get("price"),
            "meta": signal.get("meta", {}),
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.ea_url,
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Signal sent to EA: {signal['symbol']} {signal['side']} (confidence: {signal.get('confidence', 0):.2%})")
                    return True
                else:
                    logger.error(f"❌ Failed to send signal to EA: HTTP {response.status_code} - {response.text}")
                    return False
                    
        except httpx.TimeoutException:
            logger.error(f"⏱️ Timeout sending signal to EA at {self.ea_url}")
            return False
        except httpx.ConnectError:
            logger.error(f"🔌 Connection error to EA server at {self.ea_url}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending signal to EA: {e}")
            return False
    
    async def push_pending_signals(self) -> int:
        """
        Push all pending signals from the queue to the EA
        
        Returns:
            int: Number of signals successfully sent
        """
        sent_count = 0
        
        try:
            with engine.connect() as conn:
                # Get pending signals
                result = conn.execute(
                    text("""
                        SELECT id, ts, symbol, timeframe, side, confidence,
                               sl_pips, tp_pips, meta
                        FROM public.signals_queue
                        WHERE status = 'PENDING'
                          AND (now() - ts) <= (ttl_sec || ' seconds')::interval
                        ORDER BY ts DESC
                        LIMIT 100
                    """)
                )
                
                signals = result.mappings().all()
                
                if not signals:
                    logger.debug("No pending signals to send")
                    return 0
                
                logger.info(f"Found {len(signals)} pending signals to send to EA")
                
                for signal in signals:
                    signal_dict = {
                        "id": signal["id"],
                        "timestamp": signal["ts"].isoformat(),
                        "symbol": signal["symbol"],
                        "timeframe": signal["timeframe"],
                        "side": signal["side"],
                        "confidence": signal["confidence"],
                        "sl_pips": signal["sl_pips"],
                        "tp_pips": signal["tp_pips"],
                        "meta": signal["meta"] or {},
                    }
                    
                    success = await self.send_signal(signal_dict)
                    
                    if success:
                        # Update signal status to SENT
                        with engine.begin() as update_conn:
                            update_conn.execute(
                                text("""
                                    UPDATE public.signals_queue
                                    SET status = 'SENT'
                                    WHERE id = :signal_id
                                """),
                                {"signal_id": signal["id"]}
                            )
                        sent_count += 1
                    
        except Exception as e:
            logger.error(f"Error pushing pending signals: {e}")
        
        logger.info(f"Successfully sent {sent_count} signals to EA")
        return sent_count
    
    async def test_connection(self) -> bool:
        """
        Test connection to EA server
        
        Returns:
            bool: True if connection is successful
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Try a simple GET request to check connectivity
                response = await client.get(
                    f"http://{EA_SERVER_IP}:{EA_SERVER_PORT}/health",
                    headers={"X-API-Key": self.api_key}
                )
                return response.status_code in [200, 404]  # 404 is ok, means server is reachable
        except Exception as e:
            logger.error(f"EA connection test failed: {e}")
            return False


# Singleton instance
_ea_communicator = None


def get_ea_communicator() -> EACommunicator:
    """Get singleton instance of EA communicator"""
    global _ea_communicator
    if _ea_communicator is None:
        _ea_communicator = EACommunicator()
    return _ea_communicator
