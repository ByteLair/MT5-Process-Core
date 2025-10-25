# EA Communication Quick Start

## Overview

This system enables automatic communication between the AI trading system and your Expert Advisor (EA) at IP 192.168.15.18.

## Quick Setup

### 1. Configure Environment

Edit `.env` file (or create from `.env.example`):

```bash
# EA Server Configuration
EA_SERVER_IP=192.168.15.18
EA_SERVER_PORT=8080
EA_API_KEY=mt5_trading_secure_key_2025_prod
EA_PUSH_INTERVAL=30
EA_PUSH_ENABLED=true
```

### 2. Start All Services

```bash
# Start entire stack including EA pusher
docker compose up -d

# Check EA pusher status
docker compose ps ea-pusher
docker compose logs -f ea-pusher
```

### 3. Train AI Model (First Time)

```bash
# Prepare training dataset
docker compose run --rm ml-trainer python prepare_dataset.py

# Train the model
docker compose run --rm ml-trainer python train_model.py

# Verify model was created
docker compose exec api ls -la /models/rf_m1.pkl
```

### 4. Generate Your First Signal

```bash
# Using curl
curl -X POST "http://localhost:18003/ea/generate-signal" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod" \
  -d '{
    "symbol": "EURUSD",
    "timeframe": "M1",
    "force": false
  }'

# Response example:
# {
#   "success": true,
#   "message": "Signal generated and added to queue",
#   "signal": {
#     "signal_id": "abc-123",
#     "symbol": "EURUSD",
#     "side": "BUY",
#     "confidence": 0.78,
#     "sl_pips": 20,
#     "tp_pips": 40
#   }
# }
```

### 5. Test EA Connection

```bash
curl -X GET "http://localhost:18003/ea/test-connection" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod"

# Response:
# {
#   "connected": true,
#   "ea_server": "192.168.15.18:8080",
#   "message": "✅ Connected"
# }
```

### 6. Check Queue Status

```bash
curl -X GET "http://localhost:18003/ea/queue-status" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod"
```

## How It Works

```
Market Data → Features → AI Model → Signal Generation → Queue → EA Pusher → EA Server
                                                                    ↓
                                                            Every 30 seconds
```

1. **Data Collection**: EA sends market data to `/ingest` endpoint
2. **Feature Calculation**: System calculates technical indicators
3. **AI Prediction**: ML model predicts trade direction and confidence
4. **Signal Generation**: If confidence > 55%, creates BUY/SELL signal
5. **Queue**: Signal stored in database queue
6. **Automatic Push**: Background worker pushes signals every 30s
7. **EA Receives**: Your EA at 192.168.15.18 receives signal via HTTP POST

## API Endpoints

All endpoints require header: `X-API-Key: mt5_trading_secure_key_2025_prod`

### POST /ea/generate-signal
Generate a trading signal from AI prediction

**Body:**
```json
{
  "symbol": "EURUSD",
  "timeframe": "M1",
  "force": false
}
```

### POST /ea/push-signals
Manually trigger push of all pending signals

### GET /ea/test-connection
Test connection to EA server

### GET /ea/queue-status
Get status of signals queue

## EA Server Requirements

Your EA server at 192.168.15.18:8080 must implement:

**Endpoint:** POST `/signals`

**Headers:**
- `Content-Type: application/json`
- `X-API-Key: mt5_trading_secure_key_2025_prod`

**Request Body:**
```json
{
  "signal_id": "uuid",
  "timestamp": "2025-10-25T10:30:00Z",
  "symbol": "EURUSD",
  "timeframe": "M1",
  "side": "BUY",
  "confidence": 0.78,
  "sl_pips": 20,
  "tp_pips": 40,
  "price": 1.0950,
  "meta": {}
}
```

**Expected Response:**
```json
{
  "success": true,
  "ticket": 12345678
}
```

## Monitoring

### View Logs
```bash
# EA Pusher logs
docker compose logs -f ea-pusher

# API logs
docker compose logs -f api

# All services
docker compose logs -f
```

### Check Service Status
```bash
# Check all services
docker compose ps

# Check specific service
docker compose ps ea-pusher
```

### Database Queries
```bash
# Connect to database
docker compose exec db psql -U trader -d mt5_trading

# Check pending signals
SELECT * FROM public.signals_queue WHERE status = 'PENDING';

# Check sent signals
SELECT * FROM public.signals_queue WHERE status = 'SENT' ORDER BY ts DESC LIMIT 10;

# Check signal counts by status
SELECT status, COUNT(*) FROM public.signals_queue GROUP BY status;
```

## Troubleshooting

### EA Not Receiving Signals

1. **Check EA server is accessible:**
   ```bash
   ping 192.168.15.18
   curl http://192.168.15.18:8080/health
   ```

2. **Check EA pusher is running:**
   ```bash
   docker compose ps ea-pusher
   docker compose logs ea-pusher
   ```

3. **Test connection from API:**
   ```bash
   curl -X GET "http://localhost:18003/ea/test-connection" \
     -H "X-API-Key: mt5_trading_secure_key_2025_prod"
   ```

4. **Check firewall on EA server:**
   - Ensure port 8080 is open
   - Allow incoming connections from API server

### No Signals Being Generated

1. **Check if model exists:**
   ```bash
   docker compose exec api ls -la /models/rf_m1.pkl
   ```

2. **Train model if missing:**
   ```bash
   docker compose run --rm ml-trainer python train_model.py
   ```

3. **Check if features table has data:**
   ```bash
   docker compose exec db psql -U trader -d mt5_trading \
     -c "SELECT COUNT(*) FROM public.features_m1;"
   ```

4. **Force signal generation:**
   ```bash
   curl -X POST "http://localhost:18003/ea/generate-signal" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: mt5_trading_secure_key_2025_prod" \
     -d '{"symbol": "EURUSD", "timeframe": "M1", "force": true}'
   ```

### Worker Not Starting

1. **Check logs:**
   ```bash
   docker compose logs ea-pusher
   ```

2. **Check environment variables:**
   ```bash
   docker compose exec ea-pusher env | grep EA_
   ```

3. **Restart service:**
   ```bash
   docker compose restart ea-pusher
   ```

4. **Rebuild if needed:**
   ```bash
   docker compose up -d --build ea-pusher
   ```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EA_SERVER_IP` | 192.168.15.18 | IP address of EA server |
| `EA_SERVER_PORT` | 8080 | Port EA is listening on |
| `EA_API_KEY` | mt5_trading_secure_key_2025_prod | API key for authentication |
| `EA_PUSH_INTERVAL` | 30 | Push interval in seconds |
| `EA_PUSH_ENABLED` | true | Enable/disable automatic pushing |
| `EA_REQUEST_TIMEOUT` | 10 | HTTP request timeout in seconds |

### Adjusting Push Interval

```bash
# In .env file
EA_PUSH_INTERVAL=15  # Push every 15 seconds (more frequent)
# or
EA_PUSH_INTERVAL=60  # Push every 60 seconds (less frequent)

# Restart to apply
docker compose restart ea-pusher
```

### Disable Auto-Push (Manual Only)

```bash
# In .env file
EA_PUSH_ENABLED=false

# Use manual push endpoint when needed:
curl -X POST "http://localhost:18003/ea/push-signals" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod"
```

## Testing

### Run Test Script

```bash
python scripts/test_ea_communication.py
```

This will test:
- Configuration loading
- EA communicator initialization
- EA server connection
- Database connection
- Model existence
- Signal generation logic

## Next Steps

1. ✅ Configure environment variables
2. ✅ Start all services
3. ✅ Train AI model
4. ✅ Generate test signal
5. ✅ Verify EA receives signal
6. 🔧 Implement EA server endpoint (on EA side)
7. 🔧 Monitor and adjust configuration

## Support

For detailed documentation, see:
- [Complete Documentation](./docs/AI_TRAINING_EA_COMMUNICATION.md)
- [EA Integration Guide](./docs/guides/EA_INTEGRATION_GUIDE.md)
- [API Documentation](http://localhost:18003/docs)

For issues:
1. Check logs: `docker compose logs -f ea-pusher`
2. Test connection: `curl http://localhost:18003/ea/test-connection -H "X-API-Key: ..."`
3. Review this guide
4. Check detailed documentation
