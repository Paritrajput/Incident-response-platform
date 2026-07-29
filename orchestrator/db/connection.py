import os
import psycopg2
from psycopg2 import pool
from psycopg2 import InterfaceError, OperationalError
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
_pool = None


def init_pool():
    global _pool
    _pool = pool.ThreadedConnectionPool(1, 10, DATABASE_URL)
    print("Database connection pool ready", flush=True)

def get_conn():
    """Return a live pooled connection, replacing idle Neon connections if needed."""
    conn = _pool.getconn()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    except (InterfaceError, OperationalError):
        # Neon may close an idle SSL connection between pool checkouts.
        _pool.putconn(conn, close=True)
        conn = _pool.getconn()
        conn.autocommit = True
    return conn


def put_conn(conn):
    _pool.putconn(conn)


def close_pool():
    if _pool:
        _pool.closeall()
