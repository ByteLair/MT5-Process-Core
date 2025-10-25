# 🤖 AI Training and EA Communication System

## Overview

This system enables the MT5 Process Core to:
1. Train AI models for trading decisions
2. Generate trading signals based on AI predictions
3. Push signals to the Expert Advisor (EA) server automatically

## Architecture

```
┌─────────────────┐
│   Market Data   │
│  (TimescaleDB)  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  AI Training    │ ← Manual: python ml/train_model.py
│  (RandomForest) │ ← Scheduled: via scheduler
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Signal          │
│ Generation      │ ← POST /ea/generate-signal
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Signals Queue   │
│  (Database)     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ EA Pusher       │ ← Background worker (run_ea_pusher.py)
│ Worker          │    Runs every 30s
└────────┬────────┘
         │ HTTP POST
         ↓
┌─────────────────┐
│  EA Server      │
│ 192.168.15.18   │ ← Expert Advisor (MetaTrader 5)
│  Port: 8080     │
└─────────────────┘
```

## Components

### 1. AI Training

The system uses RandomForest models trained on market data with technical indicators.

#### Training Script
Location: `ml/train_model.py`

Features used:
- Price returns (1, 5, 10 periods)
- Moving averages (5, 10, 20, 50 periods)
- Standard deviations
- RSI (14 periods)
- Volume EMA

#### Manual Training
```bash
# Prepare dataset
cd ml
python prepare_dataset.py

# Train model
python train_model.py
```

#### Docker Training
```bash
docker compose run --rm ml-trainer python train_model.py
```

The trained model is saved to `/models/rf_m1.pkl`

### 2. Signal Generation

#### Automatic Generation
Signals can be generated automatically via the scheduler or manually via API endpoint.

#### Manual Generation via API
```bash
curl -X POST "http://localhost:18001/ea/generate-signal" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod" \
  -d '{
    "symbol": "EURUSD",
    "timeframe": "M1",
    "force": false
  }'
```

Response:
```json
{
  "success": true,
  "message": "Signal generated and added to queue",
  "signal": {
    "signal_id": "550e8400-e29b-41d4-a716-446655440000",
    "symbol": "EURUSD",
    "timeframe": "M1",
    "side": "BUY",
    "confidence": 0.78,
    "sl_pips": 20,
    "tp_pips": 40,
    "timestamp": "2025-10-25T10:30:00Z"
  }
}
```

#### Signal Decision Logic
- **Confidence >= 0.55**: Generate BUY signal
- **Confidence <= 0.45**: Generate SELL signal (inverted)
- **0.45 < Confidence < 0.55**: No signal (unless `force=true`)

### 3. EA Communication Service

#### Background Worker
Location: `api/run_ea_pusher.py`

This worker runs continuously and:
- Checks for pending signals every 30 seconds (configurable)
- Pushes signals to the EA server at 192.168.15.18:8080
- Updates signal status to 'SENT' after successful delivery
- Logs all operations

#### Running the Worker

**Docker Compose** (recommended):
Add to `docker-compose.yml`:
```yaml
  ea-pusher:
    build: ./api
    container_name: mt5_ea_pusher
    restart: unless-stopped
    env_file: .env
    environment:
      - EA_SERVER_IP=192.168.15.18
      - EA_SERVER_PORT=8080
      - EA_PUSH_INTERVAL=30
      - EA_PUSH_ENABLED=true
    command: python run_ea_pusher.py
    depends_on:
      - db
```

**Manual:**
```bash
cd api
python run_ea_pusher.py
```

**Systemd Service:**
```bash
# Create systemd unit
sudo nano /etc/systemd/system/mt5-ea-pusher.service

# Enable and start
sudo systemctl enable mt5-ea-pusher
sudo systemctl start mt5-ea-pusher
```

### 4. EA Communication Module

Location: `api/app/ea_communicator.py`

This module handles:
- HTTP communication with EA server
- Signal formatting and payload preparation
- Connection testing and error handling
- Retry logic and timeout management

### 5. API Endpoints

#### Test EA Connection
```bash
curl -X GET "http://localhost:18001/ea/test-connection" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod"
```

Response:
```json
{
  "connected": true,
  "ea_server": "192.168.15.18:8080",
  "ea_url": "http://192.168.15.18:8080/signals",
  "message": "✅ Connected"
}
```

#### Check Queue Status
```bash
curl -X GET "http://localhost:18001/ea/queue-status" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod"
```

Response:
```json
{
  "success": true,
  "queue_status": {
    "PENDING": {
      "count": 5,
      "latest": "2025-10-25T10:30:00Z"
    },
    "SENT": {
      "count": 120,
      "latest": "2025-10-25T10:29:30Z"
    }
  },
  "period": "last_24_hours"
}
```

#### Manual Push Signals
```bash
curl -X POST "http://localhost:18001/ea/push-signals" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod"
```

Response:
```json
{
  "success": true,
  "sent_count": 3,
  "message": "Successfully pushed 3 signals to EA"
}
```

## Configuration

### Environment Variables

Add to `.env` file:

```bash
# EA Server Configuration
EA_SERVER_IP=192.168.15.18          # IP address of EA server
EA_SERVER_PORT=8080                  # Port EA is listening on
EA_API_KEY=mt5_trading_secure_key_2025_prod  # API key for authentication
EA_PUSH_INTERVAL=30                  # Push interval in seconds
EA_PUSH_ENABLED=true                 # Enable/disable automatic pushing
EA_REQUEST_TIMEOUT=10                # HTTP request timeout in seconds
```

### EA Server Requirements

The EA server must implement the following endpoint:

**POST** `http://192.168.15.18:8080/signals`

Headers:
```
Content-Type: application/json
X-API-Key: mt5_trading_secure_key_2025_prod
```

Request Body:
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

Expected Response:
```json
{
  "success": true,
  "ticket": 12345678
}
```

## Workflow

### Complete Flow

1. **Market Data Ingestion**
   - EA sends candles to `/ingest` endpoint
   - Data stored in TimescaleDB

2. **Feature Engineering**
   - Scheduled job calculates technical indicators
   - Features stored in `features_m1` table

3. **AI Training** (periodic or manual)
   ```bash
   docker compose run --rm ml-trainer python train_model.py
   ```

4. **Signal Generation**
   - Manual: Call `/ea/generate-signal` endpoint
   - Automatic: Scheduler runs prediction periodically
   - Signal added to `signals_queue` table

5. **Signal Pushing**
   - Background worker (`run_ea_pusher.py`) runs every 30s
   - Fetches pending signals from queue
   - Sends to EA server via HTTP POST
   - Updates status to 'SENT'

6. **EA Execution**
   - EA receives signal
   - Executes trade in MetaTrader 5
   - Sends acknowledgment back (optional)

## Monitoring

### Logs

API logs include signal generation and pushing:
```bash
# View API logs
docker compose logs -f api

# View EA pusher logs
docker compose logs -f ea-pusher
```

Example log output:
```
2025-10-25 10:30:00 - INFO - Generated signal: EURUSD BUY (confidence: 78.5%)
2025-10-25 10:30:15 - INFO - ✅ Signal sent to EA: EURUSD BUY (confidence: 78.5%)
2025-10-25 10:30:15 - INFO - 📤 Pushed 1 signals to EA
```

### Prometheus Metrics

Available metrics:
- `ea_signals_generated_total` - Total signals generated
- `ea_signals_sent_total` - Total signals sent to EA
- `ea_signals_failed_total` - Total failed signal sends
- `ea_connection_test_success` - EA connection test results

### Database Tables

#### signals_queue
Stores all generated signals waiting to be sent:
```sql
SELECT * FROM public.signals_queue 
WHERE status = 'PENDING' 
ORDER BY ts DESC;
```

#### signals_ack
Stores acknowledgments from EA:
```sql
SELECT * FROM public.signals_ack 
ORDER BY acked_at DESC 
LIMIT 10;
```

## Troubleshooting

### EA Not Receiving Signals

1. **Check connection:**
   ```bash
   curl http://192.168.15.18:8080/health
   ```

2. **Test from API:**
   ```bash
   curl -X GET "http://localhost:18001/ea/test-connection" \
     -H "X-API-Key: mt5_trading_secure_key_2025_prod"
   ```

3. **Check queue:**
   ```bash
   curl -X GET "http://localhost:18001/ea/queue-status" \
     -H "X-API-Key: mt5_trading_secure_key_2025_prod"
   ```

4. **Check worker is running:**
   ```bash
   docker compose ps ea-pusher
   docker compose logs ea-pusher
   ```

### No Signals Being Generated

1. **Check if model exists:**
   ```bash
   docker compose exec api ls -la /models/rf_m1.pkl
   ```

2. **Train model if missing:**
   ```bash
   docker compose run --rm ml-trainer python train_model.py
   ```

3. **Check features table has data:**
   ```sql
   SELECT COUNT(*) FROM public.features_m1;
   ```

4. **Manually generate signal:**
   ```bash
   curl -X POST "http://localhost:18001/ea/generate-signal" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: mt5_trading_secure_key_2025_prod" \
     -d '{"symbol": "EURUSD", "timeframe": "M1", "force": true}'
   ```

### Connection Timeouts

1. **Increase timeout:**
   ```bash
   # In .env
   EA_REQUEST_TIMEOUT=30
   ```

2. **Check network:**
   ```bash
   ping 192.168.15.18
   telnet 192.168.15.18 8080
   ```

3. **Verify firewall:**
   ```bash
   # On EA server
   sudo ufw status
   sudo ufw allow 8080/tcp
   ```

## Security

### Best Practices

1. **Use HTTPS in production:**
   ```bash
   EA_SERVER_URL=https://192.168.15.18:8443/signals
   ```

2. **Rotate API keys regularly:**
   Update `EA_API_KEY` in `.env` and on EA server

3. **Restrict network access:**
   - Use firewall rules to allow only API server IP
   - Consider VPN for EA communication

4. **Monitor failed attempts:**
   - Check logs for unauthorized access attempts
   - Set up alerts for repeated failures

## Performance

### Optimization Tips

1. **Adjust push interval:**
   - Higher interval = lower load, slower response
   - Lower interval = higher load, faster response
   ```bash
   EA_PUSH_INTERVAL=15  # 15 seconds
   ```

2. **Batch processing:**
   Worker automatically batches up to 100 signals per push

3. **Connection pooling:**
   httpx client is reused for efficiency

4. **Database indexes:**
   Indexes on `signals_queue` for fast querying

## Support

For issues or questions:
1. Check logs first
2. Review this documentation
3. Test connection and queue status
4. Contact system administrator

## References

- [EA Integration Guide](./EA_INTEGRATION_GUIDE.md)
- [API Documentation](http://localhost:18001/docs)
- [ML Training Guide](../ml/README.md)
