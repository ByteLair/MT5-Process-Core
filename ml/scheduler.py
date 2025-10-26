import os

import joblib
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine, text

try:
    from ml.utils.perf import tune_environment, tune_torch_threads

    tune_environment()
    tune_torch_threads()
except Exception:
    pass

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
MODELS_DIR = os.environ.get("MODELS_DIR", "./models")
FEATURES = [
    "close",
    "volume",
    "spread",
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "atr",
    "ma60",
    "ret_1",
]
SYMBOLS = [s.strip() for s in os.environ.get("SYMBOLS", "EURUSD,GBPUSD,USDJPY").split(",")]


def load_model():
    return joblib.load(os.path.join(MODELS_DIR, "rf_m1.pkl"))


def tick():
    m = load_model()
    with engine.begin() as conn:
        for sym in SYMBOLS:
            df = pd.read_sql(
                """
               SELECT * FROM public.features_m1
               WHERE symbol=:s ORDER BY ts DESC LIMIT 30
            """,
                conn,
                params={"s": sym},
            )
            if df.empty:
                continue
            p = float(m.predict_proba(df[FEATURES].fillna(0))[:, 1][0])
            ts = df["ts"].iloc[0]
            label = int(p >= 0.5)
            conn.execute(
                text(
                    """
              INSERT INTO public.signals(ts,symbol,timeframe,prob_up,label)
              VALUES(:ts,:s,'M1',:p,:l)
            """
                ),
                {"ts": ts, "s": sym, "p": p, "l": label},
            )


def main() -> None:
    sched = BackgroundScheduler()
    sched.add_job(tick, "interval", seconds=15, max_instances=1)
    sched.start()
    import time

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        sched.shutdown()


if __name__ == "__main__":
    main()
