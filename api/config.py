import os
def get_db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql+psycopg://trader:trader123@localhost:5432/mt5_trading")
