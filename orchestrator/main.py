"""
main.py - FastAPI application entry point.

What starts here:
  - Postgres connection pool + table creation
  - Kafka consumer thread (incidents + deploys)
  - Async consume loop (orchestrates agents)
  - Prometheus pollers (one per user with Prometheus configured)

Endpoints:
  POST /auth/signup              - create account, get API key
  GET  /auth/me                  - who am I
  POST /integrations/slack       - connect Slack
  POST /integrations/prometheus  - connect Prometheus
  POST /integrations/github      - connect GitHub
  GET  /integrations/            - list my integrations
  GET  /incidents/               - my incident history
  POST /webhooks/github          - GitHub webhook receiver
  GET  /ws                       - WebSocket live feed
  GET  /health                   - liveness check
"""

import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaProducer

from config import KAFKA_BROKER
from consumer import consume_loop, recent_diagnoses, _kafka_consumer_thread
from websocket_manager import manager
from logger import log
from db.connection import init_pool, close_pool
from db.models import init_db, get_all_users_with_integration
from integrations.prometheus import run_poller
from routers import auth, integrations, incidents
from integrations.github import router as github_router
import integrations.github as _gh

from db.models import get_recent_deploys
from agents import deploy_correlator as dc
from config import FRONTEND_URLS

# log(
#     "info",
#     "github module loaded",
#     module=_gh.__file__,
# )

def make_producer() -> KafkaProducer:
    return KafkaProducer(bootstrap_servers=KAFKA_BROKER)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log("info", "orchestrator starting up")

    # Init Postgres.
    init_pool()
    init_db()
    log("info", "database ready")


    # Load recent deploys from DB into correlator cache
    recent = get_recent_deploys(minutes=60)
    for deploy in recent:
        dc.record_deploy(deploy)
    log("info", "deploy cache restored from db", count=len(recent))


    try:
        producer = make_producer()
    except Exception as e:
        log(
            "error",
            "failed to create kafka producer",
            error=str(e),
        )
        raise
    loop = asyncio.get_running_loop()

    # Start Kafka consumer thread.
    loop.run_in_executor(None, _kafka_consumer_thread, loop)

    # Start async processing loop.
    consume_task = asyncio.create_task(consume_loop(producer))

    # Start one Prometheus poller per user that has it configured.
    prometheus_users = get_all_users_with_integration("prometheus")
    poller_tasks = []
    for user in prometheus_users:
        task = asyncio.create_task(
            run_poller(user["user_id"], user["config"], producer)
        )
        poller_tasks.append(task)
    log("info", "prometheus pollers started", count=len(poller_tasks))

    log("info", "orchestrator ready")
    yield

    # Cleanup.
    consume_task.cancel()

    await asyncio.gather(
        consume_task,
        *poller_tasks,
        return_exceptions=True,
    )

    producer.close()
    close_pool()


app = FastAPI(
    title="Incident Response Platform API",
    description="Real-time multi-agent incident diagnosis as a service.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Routers.
app.include_router(auth.router)
app.include_router(integrations.router)
app.include_router(incidents.router)
app.include_router(github_router)


@app.get("/health")
async def health():
    status = {
        "status": "ok",
        "version": "1.0.0",
        "components": {}
    }

    # Check Kafka
    try:
        from kafka import KafkaAdminClient
        admin = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            request_timeout_ms=3000
        )
        topics = admin.list_topics()
        admin.close()
        status["components"]["kafka"] = {
            "status": "ok",
            "topics": len(topics)
        }
    except Exception as e:
        status["components"]["kafka"] = {"status": "error", "error": str(e)}
        status["status"] = "degraded"

    # Check Postgres/Neon
    try:
        from db.connection import get_conn, put_conn
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        put_conn(conn)
        status["components"]["database"] = {"status": "ok"}
    except Exception as e:
        status["components"]["database"] = {"status": "error", "error": str(e)}
        status["status"] = "degraded"

    # Check Prometheus (for each user who has it configured)
    try:
        import httpx
        from db.models import get_all_users_with_integration
        prometheus_users = get_all_users_with_integration("prometheus")
        if prometheus_users:
            url = prometheus_users[0]["config"].get("prometheus_url", "")
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(f"{url}/-/healthy")
                status["components"]["prometheus"] = {
                    "status": "ok" if resp.status_code == 200 else "error",
                    "url": url
                }
        else:
            status["components"]["prometheus"] = {"status": "not_configured"}
    except Exception as e:
        status["components"]["prometheus"] = {"status": "error", "error": str(e)}

    # Check WebSocket connections
    status["components"]["websocket"] = {
        "status": "ok",
        "connected_clients": len(manager.active_connections)
    }

    # Check recent activity
    status["components"]["pipeline"] = {
        "status": "ok",
        "recent_diagnoses": len(recent_diagnoses),
        "last_diagnosis": recent_diagnoses[-1]["timestamp"] if recent_diagnoses else None
    }

    return status


@app.get("/status")
async def status():
    return {
        "recent_diagnoses_count": len(recent_diagnoses),
        "recent_diagnoses": recent_diagnoses[-5:],
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    log("info", "dashboard client connected")
    try:
        for diagnosis in recent_diagnoses[-5:]:
            await websocket.send_json(diagnosis)
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        log("info", "dashboard client disconnected")