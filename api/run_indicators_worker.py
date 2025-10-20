import os
from app.indicators_worker import run_loop

if __name__ == "__main__":
    interval = int(os.getenv("INDICATORS_INTERVAL", "60"))
    run_loop(interval_sec=interval)
