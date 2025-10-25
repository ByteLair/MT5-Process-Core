"""
Example EA Server Implementation
This is a reference implementation showing what the EA server needs to implement
to receive trading signals from the AI system.

IMPORTANT: This is just an example. Your actual EA implementation should:
1. Receive signals via HTTP POST
2. Execute trades in MetaTrader 5
3. Send acknowledgments back

To run this example server:
    python examples/ea_server_example.py

The AI system will send signals to: http://192.168.15.18:8080/signals
"""
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn


app = FastAPI(title="EA Server Example")

# Expected API key (should match EA_API_KEY in main system)
EXPECTED_API_KEY = "mt5_trading_secure_key_2025_prod"

# Store received signals for demonstration
received_signals = []


class TradingSignal(BaseModel):
    """Trading signal from AI system"""
    signal_id: str
    timestamp: str
    symbol: str
    timeframe: str
    side: str  # "BUY", "SELL", "CLOSE", "NONE"
    confidence: float
    sl_pips: int
    tp_pips: int
    price: Optional[float] = None
    meta: Optional[Dict] = None


class SignalResponse(BaseModel):
    """Response after receiving signal"""
    success: bool
    ticket: Optional[int] = None
    message: Optional[str] = None


def validate_api_key(x_api_key: str = Header(None)):
    """Validate API key from header"""
    if not x_api_key or x_api_key != EXPECTED_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/signals", response_model=SignalResponse)
async def receive_signal(
    signal: TradingSignal,
    x_api_key: str = Header(None)
):
    """
    Receive trading signal from AI system
    
    This endpoint receives signals and should:
    1. Validate the signal
    2. Execute trade in MT5 (not implemented in this example)
    3. Return ticket number or error
    """
    # Validate API key
    validate_api_key(x_api_key)
    
    # Log received signal
    print("\n" + "=" * 60)
    print(f"📥 RECEIVED TRADING SIGNAL")
    print("=" * 60)
    print(f"Signal ID:   {signal.signal_id}")
    print(f"Timestamp:   {signal.timestamp}")
    print(f"Symbol:      {signal.symbol}")
    print(f"Timeframe:   {signal.timeframe}")
    print(f"Side:        {signal.side}")
    print(f"Confidence:  {signal.confidence:.2%}")
    print(f"SL (pips):   {signal.sl_pips}")
    print(f"TP (pips):   {signal.tp_pips}")
    if signal.price:
        print(f"Price:       {signal.price}")
    print("=" * 60)
    
    # Store signal for demonstration
    received_signals.append(signal.dict())
    
    # TODO: Here you would implement the actual MT5 trading logic
    # Example:
    # 1. Connect to MT5
    # 2. Check if symbol is available
    # 3. Calculate lot size
    # 4. Execute trade with SL/TP
    # 5. Return ticket number
    
    # For this example, we'll just return a fake ticket
    fake_ticket = len(received_signals) * 12345
    
    print(f"✅ Signal accepted - Ticket: {fake_ticket}\n")
    
    return SignalResponse(
        success=True,
        ticket=fake_ticket,
        message=f"Signal received and queued for execution"
    )


@app.get("/signals/history")
async def get_signal_history(x_api_key: str = Header(None)):
    """
    Get history of received signals
    This is just for demonstration/debugging
    """
    validate_api_key(x_api_key)
    
    return {
        "total_signals": len(received_signals),
        "signals": received_signals[-10:]  # Last 10 signals
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "EA Server Example",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "receive_signal": "POST /signals",
            "signal_history": "GET /signals/history"
        },
        "note": "This is an example implementation. Replace with actual MT5 integration."
    }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 EA SERVER EXAMPLE - STARTING")
    print("=" * 60)
    print("This is a reference implementation showing what the EA")
    print("server needs to implement to receive AI trading signals.")
    print()
    print("Server will listen on: http://0.0.0.0:8080")
    print("Expected API Key: mt5_trading_secure_key_2025_prod")
    print()
    print("Endpoints:")
    print("  GET  /health         - Health check")
    print("  POST /signals        - Receive trading signal")
    print("  GET  /signals/history - View received signals")
    print()
    print("To test from AI system:")
    print("  1. Set EA_SERVER_IP=192.168.15.18 in .env")
    print("  2. Start this server on the EA machine")
    print("  3. Generate signal: POST /ea/generate-signal")
    print("  4. Watch signals arrive here")
    print("=" * 60)
    print()
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )
