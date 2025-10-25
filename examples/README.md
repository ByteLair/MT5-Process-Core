# Examples

This directory contains example implementations and reference code.

## EA Server Example

**File:** `ea_server_example.py`

A reference implementation showing what the EA server needs to implement to receive trading signals from the AI system.

### What It Does

This example server:
- Listens on port 8080 for incoming signals
- Validates API key authentication
- Receives trading signals via HTTP POST
- Logs all received signals
- Returns acknowledgment with ticket number
- Provides a history endpoint to view received signals

### How to Use

1. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn
   ```

2. **Run the example server:**
   ```bash
   python examples/ea_server_example.py
   ```

3. **Test from the AI system:**
   ```bash
   # Generate a signal
   curl -X POST "http://localhost:18003/ea/generate-signal" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: mt5_trading_secure_key_2025_prod" \
     -d '{"symbol": "EURUSD", "timeframe": "M1"}'
   
   # Watch the example server receive it!
   ```

### Implementation Notes

The actual EA implementation should:

1. **Receive signals** - HTTP POST endpoint at `/signals`
2. **Validate API key** - Check `X-API-Key` header
3. **Execute trades** - Integrate with MetaTrader 5
4. **Handle errors** - Return appropriate error messages
5. **Send acknowledgments** - Return success/failure and ticket number

### Signal Format

Signals are sent as JSON:
```json
{
  "signal_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-25T10:30:00Z",
  "symbol": "EURUSD",
  "timeframe": "M1",
  "side": "BUY",
  "confidence": 0.78,
  "sl_pips": 20,
  "tp_pips": 40,
  "price": 1.0950,
  "meta": {
    "model": "rf_m1",
    "label": 1
  }
}
```

### Adapting for Production

To adapt this example for production:

1. Replace the fake ticket number with actual MT5 integration
2. Add proper error handling and validation
3. Implement position sizing logic
4. Add risk management checks
5. Store trade history in database
6. Add logging and monitoring
7. Implement trade acknowledgment back to main system

### Integration with MT5

Example MT5 integration (pseudocode):

```python
import MetaTrader5 as mt5

def execute_trade(signal):
    # Initialize MT5
    if not mt5.initialize():
        return {"success": False, "error": "MT5 not initialized"}
    
    # Prepare trade request
    symbol = signal.symbol
    side = mt5.ORDER_TYPE_BUY if signal.side == "BUY" else mt5.ORDER_TYPE_SELL
    
    # Get symbol info
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return {"success": False, "error": f"Symbol {symbol} not found"}
    
    # Calculate lot size
    lot = 0.01  # Fixed for example, should be calculated
    
    # Get current price
    price = mt5.symbol_info_tick(symbol).ask if side == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).bid
    
    # Calculate SL/TP
    point = symbol_info.point
    sl = price - signal.sl_pips * point * 10 if side == mt5.ORDER_TYPE_BUY else price + signal.sl_pips * point * 10
    tp = price + signal.tp_pips * point * 10 if side == mt5.ORDER_TYPE_BUY else price - signal.tp_pips * point * 10
    
    # Prepare request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": side,
        "price": price,
        "sl": sl,
        "tp": tp,
        "magic": 234000,
        "comment": f"AI Signal {signal.signal_id[:8]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    # Send order
    result = mt5.order_send(request)
    
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        return {
            "success": True,
            "ticket": result.order,
            "price": result.price
        }
    else:
        return {
            "success": False,
            "error": f"Order failed: {result.retcode}"
        }
```

## Additional Examples

You can add more examples here:
- `backtest_example.py` - Example backtesting script
- `signal_generator_example.py` - Example custom signal generator
- `risk_manager_example.py` - Example risk management module

## Contributing

When adding examples:
1. Include clear documentation in the file
2. Add entry to this README
3. Keep examples simple and focused
4. Include usage instructions
5. Show both basic and advanced usage
