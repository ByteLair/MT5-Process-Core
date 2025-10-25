"""
EA Signal Pusher Worker
Background worker that periodically pushes AI trading signals to the EA
"""
import asyncio
import logging
import os
import signal
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ea_communicator import get_ea_communicator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
PUSH_INTERVAL = int(os.getenv("EA_PUSH_INTERVAL", "30"))  # seconds
ENABLED = os.getenv("EA_PUSH_ENABLED", "true").lower() == "true"

# Global flag for graceful shutdown
running = True


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info("Shutdown signal received, stopping EA pusher...")
    running = False


async def push_signals_loop():
    """Main loop that pushes signals to EA periodically"""
    ea_comm = get_ea_communicator()
    
    logger.info(f"🚀 EA Signal Pusher started - pushing every {PUSH_INTERVAL}s")
    logger.info(f"📡 EA Server: {os.getenv('EA_SERVER_IP', '192.168.15.18')}:{os.getenv('EA_SERVER_PORT', '8080')}")
    
    # Test connection on startup
    if await ea_comm.test_connection():
        logger.info("✅ EA server connection test successful")
    else:
        logger.warning("⚠️ EA server connection test failed - will retry during operation")
    
    iteration = 0
    while running:
        try:
            iteration += 1
            logger.debug(f"Starting push iteration {iteration}")
            
            # Push pending signals
            sent_count = await ea_comm.push_pending_signals()
            
            if sent_count > 0:
                logger.info(f"📤 Pushed {sent_count} signals to EA")
            
        except Exception as e:
            logger.error(f"Error in push loop: {e}", exc_info=True)
        
        # Wait for next iteration
        for _ in range(PUSH_INTERVAL):
            if not running:
                break
            await asyncio.sleep(1)
    
    logger.info("EA Signal Pusher stopped")


async def main():
    """Main entry point"""
    if not ENABLED:
        logger.warning("EA Signal Pusher is disabled (EA_PUSH_ENABLED=false)")
        return
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await push_signals_loop()
    except Exception as e:
        logger.error(f"Fatal error in EA pusher: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
