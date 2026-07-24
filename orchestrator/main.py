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
import integrations.github as _gh; print(f"[STARTUP] github module loaded from: {_gh.__file__}", flush=True)


def make_producer() -> KafkaProducer:
    return KafkaProducer(bootstrap_servers=KAFKA_BROKER)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log("info", "orchestrator starting up")

    # Init Postgres.
    init_pool()
    init_db()
    log("info", "database ready")

    producer = make_producer()
    loop = asyncio.get_event_loop()

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
    for t in poller_tasks:
        t.cancel()
    producer.close()
    close_pool()
    log("info", "orchestrator shut down cleanly")


app = FastAPI(
    title="Incident Response Platform API",
    description="Real-time multi-agent incident diagnosis as a service.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:3000", "http://127.0.0.1:3000"],
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
    return {"status": "ok", "version": "1.0.0"}


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
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        log("info", "dashboard client disconnected")