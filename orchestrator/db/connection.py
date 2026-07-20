"""
db/connection.py - Postgres connection using psycopg2.

Kept intentionally simple: a single connection pool shared across
the app, created at startup and closed at shutdown. No ORM — plain
SQL so you can see exactly what's happening.
"""

import os
from urllib.parse import quote

import psycopg2
from dotenv import load_dotenv
from psycopg2 import pool


def _load_environment() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    for candidate in [
        os.path.join(current_dir, "..", ".env"),
        os.path.join(current_dir, "..", "..", ".env"),
    ]:
        if os.path.exists(candidate):
            load_dotenv(dotenv_path=candidate, override=False)


_load_environment()


def _normalize_database_url(raw_url: str) -> str:
    if not raw_url or "://" not in raw_url:
        return raw_url

    scheme, remainder = raw_url.split("://", 1)
    if "@" not in remainder:
        return raw_url

    auth, host = remainder.rsplit("@", 1)
    if ":" not in auth:
        return raw_url

    username, password = auth.split(":", 1)
    return f"{scheme}://{username}:{quote(password, safe='%')}@{host}"


def _build_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL")
    if raw_url:
        return _normalize_database_url(raw_url)

    password = os.getenv("POSTGRES_PASSWORD", "localpassword")
    encoded_password = quote(password, safe="")
    return f"postgresql://admin:{encoded_password}@localhost:5432/incidents"


DATABASE_URL = _build_database_url()

# Thread-safe connection pool (min 1, max 10 connections).
_pool: pool.ThreadedConnectionPool = None


def init_pool():
    global _pool
    _pool = pool.ThreadedConnectionPool(1, 10, DATABASE_URL)


def get_conn():
    return _pool.getconn()


def put_conn(conn):
    _pool.putconn(conn)


def close_pool():
    if _pool:
        _pool.closeall()