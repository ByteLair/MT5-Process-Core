import os, logging
import psycopg2

DSN = os.getenv("DATABASE_URL","").replace("postgresql://","postgresql://")

def check_db_connection() -> bool:
    try:
        with psycopg2.connect(DSN) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception as e:
        logging.exception("DB check failed: %s", e)
        return False
