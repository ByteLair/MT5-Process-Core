"""
Centralized SQLAlchemy engine configured for PgBouncer + optimized pooling.

Exports a singleton `engine` to be reused across the application.
"""

from config import get_db_connect_args, get_db_url, get_sqlalchemy_pool_config
from sqlalchemy import create_engine

# Create a single Engine instance for the entire app/process
engine = create_engine(
    get_db_url(),
    **get_sqlalchemy_pool_config(),
    connect_args=get_db_connect_args(),
    future=True,
)
