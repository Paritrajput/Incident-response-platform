"""
db/models.py - Database schema and helper functions.

Three tables:
  users        - one row per account (email, api_key, created_at)
  integrations - one row per connected service (Slack, Prometheus, GitHub)
                 per user. Stores credentials/config as JSON.
  incidents    - every diagnosed incident stored here for history + eval.

Plain SQL, no ORM. Each function gets a connection from the pool,
does its work, and returns it. Simple and explicit.
"""

import json
import secrets
from datetime import datetime, timezone

from db.connection import get_conn, put_conn


# ── Schema creation ──────────────────────────────────────────────────────────

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    api_key     TEXT UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS integrations (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,        -- 'slack' | 'prometheus' | 'github'
    config      JSONB NOT NULL,       -- credentials and settings
    enabled     BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (user_id, type)
);

CREATE TABLE IF NOT EXISTS incidents (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    trace_id        TEXT NOT NULL,
    service         TEXT NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    latency_ms      INTEGER,
    final_diagnosis JSONB,
    agent_results   JSONB,
    disagreement_score FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incidents_user_id ON incidents(user_id);
CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(timestamp DESC);
"""


def init_db():
    """Create tables if they don't exist. Safe to call on every startup."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLES_SQL)
        conn.commit()
    finally:
        put_conn(conn)


# ── User functions ────────────────────────────────────────────────────────────

def create_user(email: str) -> dict:
    """Create a new user with a random API key. Returns the user row."""
    api_key = secrets.token_urlsafe(32)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, api_key) VALUES (%s, %s) "
                "RETURNING id, email, api_key, created_at",
                (email, api_key)
            )
            row = cur.fetchone()
        conn.commit()
        return {"id": row[0], "email": row[1], "api_key": row[2], "created_at": row[3]}
    finally:
        put_conn(conn)


def get_user_by_api_key(api_key: str) -> dict | None:
    """Look up a user by their API key. Returns None if not found."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, api_key, created_at FROM users WHERE api_key = %s",
                (api_key,)
            )
            row = cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "email": row[1], "api_key": row[2], "created_at": row[3]}
    finally:
        put_conn(conn)


def get_user_by_email(email: str) -> dict | None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, api_key, created_at FROM users WHERE email = %s",
                (email,)
            )
            row = cur.fetchone()
        if not row:
            return None
        return {"id": row[0], "email": row[1], "api_key": row[2], "created_at": row[3]}
    finally:
        put_conn(conn)


# ── Integration functions ────────────────────────────────────────────────────

def upsert_integration(user_id: int, integration_type: str, config: dict) -> dict:
    """Save or update an integration config for a user."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO integrations (user_id, type, config)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, type)
                DO UPDATE SET config = EXCLUDED.config, enabled = TRUE
                RETURNING id, type, config, enabled
            """, (user_id, integration_type, json.dumps(config)))
            row = cur.fetchone()
        conn.commit()
        return {"id": row[0], "type": row[1], "config": row[2], "enabled": row[3]}
    finally:
        put_conn(conn)


def get_integrations(user_id: int) -> list:
    """Get all enabled integrations for a user."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, type, config, enabled FROM integrations "
                "WHERE user_id = %s AND enabled = TRUE",
                (user_id,)
            )
            rows = cur.fetchall()
        return [{"id": r[0], "type": r[1], "config": r[2], "enabled": r[3]} for r in rows]
    finally:
        put_conn(conn)


def get_all_users_with_integration(integration_type: str) -> list:
    """
    Get all users who have a specific integration enabled.
    Used by the Prometheus poller to know which users to poll,
    and by Slack to know who to notify.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.email, i.config
                FROM users u
                JOIN integrations i ON i.user_id = u.id
                WHERE i.type = %s AND i.enabled = TRUE
            """, (integration_type,))
            rows = cur.fetchall()
        return [{"user_id": r[0], "email": r[1], "config": r[2]} for r in rows]
    finally:
        put_conn(conn)


# ── Incident functions ───────────────────────────────────────────────────────

def save_incident(user_id: int, diagnosis_event: dict) -> int:
    """Persist a diagnosis event to the incidents table."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO incidents
                  (user_id, trace_id, service, timestamp, latency_ms,
                   final_diagnosis, agent_results, disagreement_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                diagnosis_event["trace_id"],
                diagnosis_event["service"],
                diagnosis_event["timestamp"],
                diagnosis_event.get("latency_ms"),
                json.dumps(diagnosis_event.get("resolution", {}).get("final_diagnosis")),
                json.dumps(diagnosis_event.get("agent_results", [])),
                diagnosis_event.get("resolution", {}).get("disagreement_score"),
            ))
            incident_id = cur.fetchone()[0]
        conn.commit()
        return incident_id
    finally:
        put_conn(conn)


def get_incidents(user_id: int, limit: int = 20) -> list:
    """Fetch recent incidents for a user."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT trace_id, service, timestamp, latency_ms,
                       final_diagnosis, disagreement_score
                FROM incidents
                WHERE user_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (user_id, limit))
            rows = cur.fetchall()
        return [{
            "trace_id": r[0], "service": r[1],
            "timestamp": r[2].isoformat(), "latency_ms": r[3],
            "final_diagnosis": r[4], "disagreement_score": r[5],
        } for r in rows]
    finally:
        put_conn(conn)