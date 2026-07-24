import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
_pool = None


def init_pool():
    global _pool
    _pool = pool.ThreadedConnectionPool(1, 10, DATABASE_URL)
    print(f"Database connected: {DATABASE_URL[:40]}...", flush=True)

def get_conn():
    conn = _pool.getconn()
    conn.autocommit = True
    return conn
def put_conn(conn):
    _pool.putconn(conn)


def close_pool():
    if _pool:
        _pool.closeall()