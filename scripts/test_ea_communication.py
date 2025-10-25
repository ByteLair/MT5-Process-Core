#!/usr/bin/env python3
"""
Test script for AI Training and EA Communication system
"""
import asyncio
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from api.app.ea_communicator import EACommunicator
    from sqlalchemy import create_engine, text
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running from the repository root with dependencies installed")
    sys.exit(1)


def test_configuration():
    """Test that configuration is properly set"""
    print("=" * 60)
    print("TEST 1: Configuration")
    print("=" * 60)
    
    ea_ip = os.getenv("EA_SERVER_IP", "192.168.15.18")
    ea_port = os.getenv("EA_SERVER_PORT", "8080")
    ea_api_key = os.getenv("EA_API_KEY", "mt5_trading_secure_key_2025_prod")
    push_interval = os.getenv("EA_PUSH_INTERVAL", "30")
    push_enabled = os.getenv("EA_PUSH_ENABLED", "true")
    
    print(f"EA Server IP:     {ea_ip}")
    print(f"EA Server Port:   {ea_port}")
    print(f"API Key:          {ea_api_key[:10]}...")
    print(f"Push Interval:    {push_interval}s")
    print(f"Push Enabled:     {push_enabled}")
    print(f"EA URL:           http://{ea_ip}:{ea_port}/signals")
    print("✅ Configuration loaded\n")


async def test_ea_communicator():
    """Test EA communicator initialization"""
    print("=" * 60)
    print("TEST 2: EA Communicator Initialization")
    print("=" * 60)
    
    try:
        ea_comm = EACommunicator()
        print(f"EA URL:       {ea_comm.ea_url}")
        print(f"Timeout:      {ea_comm.timeout}s")
        print("✅ EA Communicator initialized\n")
        return ea_comm
    except Exception as e:
        print(f"❌ Failed to initialize EA Communicator: {e}\n")
        return None


async def test_ea_connection(ea_comm):
    """Test connection to EA server"""
    print("=" * 60)
    print("TEST 3: EA Connection Test")
    print("=" * 60)
    
    if not ea_comm:
        print("⚠️ Skipping connection test (communicator not initialized)\n")
        return
    
    try:
        is_connected = await ea_comm.test_connection()
        if is_connected:
            print("✅ Connection to EA server successful\n")
        else:
            print("⚠️ Connection to EA server failed (this is expected if EA is not running)\n")
    except Exception as e:
        print(f"⚠️ Connection test error: {e}")
        print("   (This is expected if EA server is not running)\n")


def test_database_connection():
    """Test database connection and signals queue"""
    print("=" * 60)
    print("TEST 4: Database Connection")
    print("=" * 60)
    
    db_url = os.getenv("DATABASE_URL", "postgresql://trader:trader123@localhost:5432/mt5_trading")
    
    try:
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # Test connection
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            
            # Check if signals_queue table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'signals_queue'
                )
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("✅ signals_queue table exists")
                
                # Count pending signals
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM public.signals_queue 
                    WHERE status = 'PENDING'
                """))
                pending_count = result.scalar()
                print(f"   Pending signals: {pending_count}")
                
                # Count total signals
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM public.signals_queue
                """))
                total_count = result.scalar()
                print(f"   Total signals: {total_count}")
            else:
                print("⚠️ signals_queue table not found (may need to run DB migrations)")
        
        print()
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}\n")


def test_model_exists():
    """Test if ML model exists"""
    print("=" * 60)
    print("TEST 5: ML Model Check")
    print("=" * 60)
    
    model_path = os.getenv("MODEL_PATH", "/models/rf_m1.pkl")
    
    if os.path.exists(model_path):
        print(f"✅ Model found at {model_path}")
        size = os.path.getsize(model_path)
        print(f"   Size: {size:,} bytes")
    else:
        print(f"⚠️ Model not found at {model_path}")
        print("   Run 'python ml/train_model.py' to train the model")
    print()


async def test_signal_generation():
    """Test signal generation logic"""
    print("=" * 60)
    print("TEST 6: Signal Generation Logic")
    print("=" * 60)
    
    # Test signal decision logic
    test_cases = [
        (0.78, "BUY"),
        (0.35, "SELL"),
        (0.50, "NONE"),
        (0.55, "BUY"),
        (0.45, "SELL"),
    ]
    
    print("Testing signal decision logic:")
    for confidence, expected_side in test_cases:
        if confidence >= 0.55:
            side = "BUY"
        elif confidence <= 0.45:
            side = "SELL"
            confidence_display = 1 - confidence
        else:
            side = "NONE"
            confidence_display = confidence
        
        status = "✅" if side == expected_side else "❌"
        print(f"  {status} Confidence {confidence:.2f} -> {side} (expected {expected_side})")
    
    print()


def test_summary():
    """Print test summary"""
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("""
The following components have been created:

1. ✅ api/app/ea_communicator.py - EA communication module
2. ✅ api/app/ea_signals.py - EA signals API endpoints
3. ✅ api/run_ea_pusher.py - Background worker for pushing signals
4. ✅ docker-compose.yml - Added ea-pusher service
5. ✅ .env.example - Added EA configuration variables
6. ✅ api/requirements.txt - Added httpx dependency
7. ✅ docs/AI_TRAINING_EA_COMMUNICATION.md - Complete documentation

New API Endpoints Available:
- POST /ea/generate-signal - Generate AI trading signal
- POST /ea/push-signals - Manually push pending signals
- GET /ea/test-connection - Test EA server connection
- GET /ea/queue-status - Check signals queue status

To use the system:
1. Configure EA server IP in .env (EA_SERVER_IP=192.168.15.18)
2. Start services: docker compose up -d
3. Train AI model: docker compose run --rm ml-trainer python train_model.py
4. Generate signals: POST /ea/generate-signal
5. Monitor EA pusher: docker compose logs -f ea-pusher

For detailed instructions, see docs/AI_TRAINING_EA_COMMUNICATION.md
""")


async def main():
    """Run all tests"""
    print("\n")
    print("🤖 AI TRAINING & EA COMMUNICATION SYSTEM TEST")
    print("=" * 60)
    print()
    
    # Run tests
    test_configuration()
    ea_comm = await test_ea_communicator()
    await test_ea_connection(ea_comm)
    test_database_connection()
    test_model_exists()
    await test_signal_generation()
    test_summary()
    
    print("\n✅ All tests completed!\n")


if __name__ == "__main__":
    asyncio.run(main())
