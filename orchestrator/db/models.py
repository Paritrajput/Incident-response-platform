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
from logger import log


#Schemas

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    username    TEXT UNIQUE NOT NULL,
    email       TEXT UNIQUE NOT NULL,
    api_key     TEXT UNIQUE NOT NULL,
    password_hash TEXT,
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

CREATE TABLE IF NOT EXISTS deploys (
    id          SERIAL PRIMARY KEY,
    service     TEXT NOT NULL,
    deploy_id   TEXT NOT NULL,
    commit_message TEXT,
    branch      TEXT,
    source      TEXT,
    timestamp   TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deploys_timestamp ON deploys(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_deploys_service ON deploys(service);
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

def create_user(username: str, email: str, password_hash: str) -> dict:
    api_key = secrets.token_urlsafe(32)

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
        """
        INSERT INTO users
            (username, email, api_key, password_hash)
        VALUES
            (%s, %s, %s, %s)
        RETURNING
            id,
            username,
            email,
            api_key,
            password_hash,
            created_at
        """,
        (
            username,
            email,
            api_key,
            password_hash,
        ),
    )

            row = cur.fetchone()
            conn.commit()

        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "api_key": row[3],
            "password_hash": row[4],
            "created_at": row[5],
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        put_conn(conn)


def regenerate_api_key(user_id: int) -> str:
    """
    Generate a brand-new API key.

    Useful if a user accidentally exposes it.
    """

    new_key = secrets.token_urlsafe(32)

    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET api_key=%s
                WHERE id=%s
                """,
                (
                    new_key,
                    user_id,
                ),
            )

            conn.commit()

        return new_key

    except Exception:
        conn.rollback()
        raise

    finally:
        put_conn(conn)

def get_user_by_api_key(api_key: str) -> dict | None:
    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, email, api_key, created_at
                FROM users
                WHERE api_key = %s
                """,
                (api_key,),
            )

            row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "api_key": row[3],
            "created_at": row[4],
        }

    finally:
        put_conn(conn)
def get_user_by_email(email: str):
    """
    Fetch a user by email.

    Returns:
        dict | None
    """

    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    username,
                    email,
                    password_hash,
                    api_key,
                    created_at
                FROM users
                WHERE email = %s
                """,
                (email,),
            )

            row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "password_hash": row[3],
            "api_key": row[4],
            "created_at": row[5],
        }

    finally:
        put_conn(conn)

        
def get_user_by_username(username: str) -> dict | None:
    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, username,api_key, email, created_at
                FROM users
                WHERE username = %s
                """,
                (username,),
            )

            row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "api_key":row[3],
            "created_at": row[4],
        }

    finally:
        put_conn(conn)

        
def get_user_by_id(user_id: int) -> dict | None:
    """
    Fetch a user by primary key.

    Used by JWT authentication.
    """

    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    username,
                    email,
                    api_key,
                    password_hash,
                    created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,),
            )

            row = cur.fetchone()

        if not row:
            return None

        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "api_key": row[3],
            "password_hash": row[4],
            "created_at": row[5],
        }

    finally:
        put_conn(conn)



def upsert_integration(user_id: int, integration_type: str, config: dict) -> dict:
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
            conn.commit()  # commit BEFORE put_conn
        return {"id": row[0], "type": row[1], "config": row[2], "enabled": row[3]}
    except Exception:
        conn.rollback()
        raise
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
        SELECT
            u.id,
            u.username,
            u.email,
            i.config
        FROM users u
        JOIN integrations i
            ON i.user_id = u.id
        WHERE
            i.type = %s
            AND i.enabled = TRUE
    """, (integration_type,))
            rows = cur.fetchall()
        return [
    {
        "user_id": r[0],
        "username": r[1],
        "email": r[2],
        "config": r[3],
    }
    for r in rows
]
    finally:
        put_conn(conn)


#Incident functions 

def save_incident(user_id: int, diagnosis_event: dict) -> int:
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
            conn.commit()  # commit BEFORE put_conn
        return incident_id
    except Exception:
        conn.rollback()
        raise
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


def save_deploy(deploy_event: dict) -> None:
    """Persist a deploy event so it survives orchestrator restarts."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO deploys
                  (service, deploy_id, commit_message, branch, source, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                deploy_event.get("service", "unknown"),
                deploy_event.get("deploy_id", ""),
                deploy_event.get("commit_message", ""),
                deploy_event.get("branch", ""),
                deploy_event.get("source", "github"),
                deploy_event.get("timestamp"),
            ))
    except Exception as e:
        log(
            "error",
            "failed to save deploy",
            error=str(e),
        )
    finally:
        put_conn(conn)


def get_recent_deploys(minutes: int = 60) -> list:
    """
    Load deploys from the last N minutes.
    Called on startup to repopulate the correlator cache.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT service, deploy_id, commit_message, branch, source, timestamp
                FROM deploys
                WHERE timestamp > NOW() - (%s * INTERVAL '1 minute')
                ORDER BY timestamp DESC
                LIMIT 100
            """, (minutes,))
            rows = cur.fetchall()
        return [{
            "service": r[0],
            "deploy_id": r[1],
            "commit_message": r[2],
            "branch": r[3],
            "source": r[4],
            "timestamp": r[5].isoformat(),
        } for r in rows]
    finally:
        put_conn(conn)