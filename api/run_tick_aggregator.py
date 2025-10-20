import os
from app.tick_aggregator import run_loop

if __name__ == "__main__":
    interval = int(os.getenv("TICK_AGG_INTERVAL", "5"))
    run_loop(interval_sec=interval)
