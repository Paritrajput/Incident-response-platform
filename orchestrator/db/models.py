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

CREATE TABLE IF NOT EXISTS applications (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',

    is_default      BOOLEAN DEFAULT FALSE,

    status          TEXT DEFAULT 'draft',

    is_deleted      BOOLEAN DEFAULT FALSE,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_applications_user
ON applications(user_id);

CREATE TABLE IF NOT EXISTS integrations (
    id          SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES applications(id) ON DELETE CASCADE,
    type        TEXT NOT NULL,        -- 'slack' | 'prometheus' | 'github'
    config      JSONB NOT NULL,       -- credentials and settings
    enabled     BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (application_id, type)
);

CREATE TABLE IF NOT EXISTS incidents (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),
    application_id  INTEGER REFERENCES applications(id),
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
CREATE INDEX IF NOT EXISTS idx_incidents_application_id ON incidents(application_id);
CREATE INDEX IF NOT EXISTS idx_incidents_timestamp ON incidents(timestamp DESC);

CREATE TABLE IF NOT EXISTS deploys (

    id SERIAL PRIMARY KEY,
    application_id INTEGER REFERENCES applications(id),
    service TEXT NOT NULL,
    deploy_id TEXT NOT NULL,
    commit_message TEXT,
    branch TEXT,
    source TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_deploys_application ON deploys(application_id);
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



def upsert_integration(application_id: int, integration_type: str, config: dict) -> dict:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO integrations (application_id, type, config)
                VALUES (%s, %s, %s)
                ON CONFLICT (application_id, type)
                DO UPDATE SET config = EXCLUDED.config, enabled = TRUE
                RETURNING id, type, config, enabled
            """, (application_id, integration_type, json.dumps(config)))
            row = cur.fetchone()
            conn.commit()  # commit BEFORE put_conn
        return {"id": row[0], "type": row[1], "config": row[2], "enabled": row[3]}
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)

def get_integrations(application_id: int):
    """Get all enabled integrations for an application."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, type, config, enabled FROM integrations "
                "WHERE application_id = %s AND enabled = TRUE",
                (application_id,)
            )
            rows = cur.fetchall()
        return [{"id": r[0], "type": r[1], "config": r[2], "enabled": r[3]} for r in rows]
    finally:
        put_conn(conn)

def get_integration(application_id: int, integration_type: str):
    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    type,
                    config,
                    enabled
                FROM integrations
                WHERE
                    application_id=%s
                    AND type=%s
            """, (application_id, integration_type))

            row = cur.fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "type": row[1],
            "config": row[2],
            "enabled": row[3],
        }

    finally:
        put_conn(conn)
def get_all_applications_with_integration(integration_type: str):
    """
    Get all applications that have a specific integration enabled.
    Used by the Prometheus poller, Slack notifier and GitHub webhook.
    """
    conn = get_conn()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    a.id,
                    a.user_id,
                    a.name,
                    u.username,
                    u.email,
                    i.config
                FROM applications a
                JOIN users u
                    ON u.id = a.user_id
                JOIN integrations i
                    ON i.application_id = a.id
                WHERE
                    i.type = %s
                    AND i.enabled = TRUE
                    AND a.is_deleted = FALSE
            """, (integration_type,))

            rows = cur.fetchall()

        return [
            {
                "application_id": r[0],
                "user_id": r[1],
                "application_name": r[2],
                "username": r[3],
                "email": r[4],
                "config": r[5],
            }
            for r in rows
        ]

    finally:
        put_conn(conn)
#Incident functions 

def save_incident(
    user_id: int,
    application_id: int,
    diagnosis_event: dict,
) -> int:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                        INSERT INTO incidents
                        (
                            user_id,
                            application_id,
                            trace_id,
                            service,
                            timestamp,
                            latency_ms,
                            final_diagnosis,
                            agent_results,
                            disagreement_score
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """
                        , (
                    user_id,
                    application_id,
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

def get_incidents(
    application_id: int,
    limit: int = 20,
):
    """Fetch recent incidents for an application."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT trace_id, service, timestamp, latency_ms,
                       final_diagnosis, agent_results, disagreement_score
                FROM incidents
                WHERE application_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (application_id, limit))
            rows = cur.fetchall()
        return [{
            "trace_id": r[0], "service": r[1],
            "timestamp": r[2].isoformat(), "latency_ms": r[3],
            # Match the live WebSocket event shape used by IncidentCard.
            "final_diagnosis": r[4],
            "agent_results": r[5] or [],
            "disagreement_score": r[6],
            "resolution": {
                "final_diagnosis": r[4] or {},
                "disagreement_score": r[6] or 0,
            },
        } for r in rows]
    finally:
        put_conn(conn)


def save_deploy(deploy_event: dict) -> None:
    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO deploys
                (
                    application_id,
                    service,
                    deploy_id,
                    commit_message,
                    branch,
                    source,
                    timestamp
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                deploy_event["application_id"],
                deploy_event.get("service", "unknown"),
                deploy_event.get("deploy_id", ""),
                deploy_event.get("commit_message", ""),
                deploy_event.get("branch", ""),
                deploy_event.get("source", "github"),
                deploy_event.get("timestamp"),
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

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
                SELECT application_id, service, deploy_id, commit_message, branch, source, timestamp
                FROM deploys
                WHERE timestamp > NOW() - (%s * INTERVAL '1 minute')
                ORDER BY timestamp DESC
                LIMIT 100
            """, (minutes,))
            rows = cur.fetchall()
            return [{
            "application_id": r[0],
            "service": r[1],
            "deploy_id": r[2],
            "commit_message": r[3],
            "branch": r[4],
            "source": r[5],
            "timestamp": r[6].isoformat(),
        } for r in rows]
    finally:
        put_conn(conn)


def get_deploys(application_id: int, limit: int = 50) -> list:
    """Fetch recent deployment events for one application."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, service, deploy_id, commit_message, branch, source, timestamp
                FROM deploys
                WHERE application_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (application_id, limit))
            rows = cur.fetchall()
        return [{
            "id": r[0],
            "service": r[1],
            "deploy_id": r[2],
            "commit_message": r[3],
            "branch": r[4],
            "source": r[5],
            "timestamp": r[6].isoformat(),
        } for r in rows]
    finally:
        put_conn(conn)


def create_application(user_id: int, name: str, description: str = ""):
    conn = get_conn()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO applications
                    (user_id, name, description)
                VALUES
                    (%s, %s, %s)
                RETURNING
                    id,
                    user_id,
                    name,
                    description,
                    is_default,
                    status
            """, (user_id, name, description))

            row = cur.fetchone()

            conn.commit()

        return {
            "id": row[0],
            "user_id": row[1],
            "name": row[2],
            "description": row[3],
            "is_default": row[4],
            "status": row[5],
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        put_conn(conn)


def get_applications(user_id: int):
    conn = get_conn()

    try:

        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    id,
                    name,
                    description,
                    is_default,
                    status,
                    created_at
                FROM applications
                WHERE
                    user_id=%s
                    AND is_deleted=FALSE
                ORDER BY created_at DESC
            """, (user_id,))

            rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "name": r[1],
                "description": r[2],
                "is_default": r[3],
                "status": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]

    finally:
        put_conn(conn)

def get_application(application_id: int):
    conn = get_conn()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    user_id,
                    name,
                    description,
                    is_default,
                    status,
                    created_at,
                    updated_at
                FROM applications
                WHERE
                    id=%s
                    AND is_deleted=FALSE
            """, (application_id,))

            row = cur.fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "user_id": row[1],
            "name": row[2],
            "description": row[3],
            "is_default": row[4],
            "status": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }

    finally:
        put_conn(conn)

def application_belongs_to_user(application_id: int, user_id: int):
    conn = get_conn()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT 1
                FROM applications
                WHERE
                    id=%s
                    AND user_id=%s
                    AND is_deleted=FALSE
            """, (application_id, user_id))

            return cur.fetchone() is not None

    finally:
        put_conn(conn)


def update_application(application_id: int, user_id: int, changes: dict):
    """Update only supported application fields and return the updated row."""
    allowed = {"name", "description", "status", "is_default"}
    changes = {key: value for key, value in changes.items() if key in allowed}
    if not changes:
        return get_application(application_id)

    assignments = ", ".join(f"{field} = %s" for field in changes)
    values = [*changes.values(), application_id, user_id]
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE applications
                SET {assignments}, updated_at = NOW()
                WHERE id = %s AND user_id = %s AND is_deleted = FALSE
                RETURNING id
            """, values)
            row = cur.fetchone()
        conn.commit()
        return get_application(row[0]) if row else None
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)


def delete_application(application_id: int, user_id: int) -> bool:
    """Soft-delete an owned application so its historical records remain intact."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE applications
                SET is_deleted = TRUE, updated_at = NOW()
                WHERE id = %s AND user_id = %s AND is_deleted = FALSE
                RETURNING id
            """, (application_id, user_id))
            deleted = cur.fetchone() is not None
        conn.commit()
        return deleted
    except Exception:
        conn.rollback()
        raise
    finally:
        put_conn(conn)
