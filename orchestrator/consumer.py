"""
consumer.py - Kafka consumer loop and orchestration logic.

Now also:
- Saves every diagnosis to Postgres (incident history)
- Sends Slack notifications to all users with Slack configured
"""

import asyncio
import json
from datetime import datetime, timezone

from kafka import KafkaConsumer, KafkaProducer

import agents.log_analyst as log_analyst
import agents.deploy_correlator as deploy_correlator
import agents.metrics_analyst as metrics_analyst
from agents.resolver import resolve
from config import KAFKA_BROKER, AGENT_TIMEOUT_SECONDS, AGENT_MAX_RETRIES
from logger import log
from trace import set_trace_id, new_trace_id
from websocket_manager import manager
from integrations import slack as slack_integration
from db.models import get_all_users_with_integration, save_incident

TOPIC_INCIDENTS = "incidents"
TOPIC_DIAGNOSES = "diagnoses"
TOPIC_DEPLOYS = "deploys"

incident_queue: asyncio.Queue = asyncio.Queue()
recent_diagnoses: list = []
MAX_RECENT = 20


def _kafka_consumer_thread(loop: asyncio.AbstractEventLoop) -> None:
    consumer = KafkaConsumer(
        TOPIC_INCIDENTS,
        TOPIC_DEPLOYS,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
        group_id="orchestrator-v2",
    )
    log("info", "kafka consumer thread started",
        topics=[TOPIC_INCIDENTS, TOPIC_DEPLOYS])

    for message in consumer:
        if message.topic == TOPIC_INCIDENTS:
            loop.call_soon_threadsafe(incident_queue.put_nowait, message.value)
        elif message.topic == TOPIC_DEPLOYS:
            deploy_correlator.record_deploy(message.value)


async def _call_agent_with_retry(agent_fn, incident: dict) -> dict:
    last_error = None
    for attempt in range(1, AGENT_MAX_RETRIES + 2):
        try:
            log("info", "calling agent",
                agent=agent_fn.__module__,
                attempt=attempt,
                service=incident["service"])
            result = await asyncio.wait_for(
                agent_fn(incident),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
            return result
        except asyncio.TimeoutError:
            last_error = f"timed out after {AGENT_TIMEOUT_SECONDS}s"
            log("warn", "agent timed out",
                agent=agent_fn.__module__, attempt=attempt,
                service=incident["service"])
        except Exception as e:
            last_error = str(e)
            log("error", "agent raised exception",
                agent=agent_fn.__module__, attempt=attempt,
                error=str(e), service=incident["service"])
        if attempt <= AGENT_MAX_RETRIES:
            await asyncio.sleep(2 ** attempt)

    return {
        "agent": agent_fn.__module__.split(".")[-1],
        "diagnosis": {
            "root_cause": "Agent unavailable",
            "confidence": "none",
            "evidence": [],
            "recommended_action": "Check agent logs",
        },
        "error": last_error,
    }


async def _notify_slack(diagnosis_event: dict):
    """Send Slack notification - deduplicated, max one message per incident."""
    slack_users = get_all_users_with_integration("slack")
    
    if not slack_users:
        log("warn", "no slack integration configured")
        return

    # Only notify the first configured user to avoid duplicates
    # In multi-tenant: match by user_id from the incident source
    user = slack_users[0]
    config = user["config"]
    
    await slack_integration.send_diagnosis(
        bot_token=config.get("bot_token", ""),
        channel_id=config.get("channel_id", ""),
        diagnosis_event=diagnosis_event,
    )


async def _save_to_db(diagnosis_event: dict):
    """
    Save incident to Postgres for all users.
    In a real multi-tenant system, we'd know which user owns this
    incident from the data source. For now, save for all users.
    """
    try:
        # Save for the first user (single-tenant for now).
        # Multi-tenant: match incident source to user_id.
        from db.models import get_conn, put_conn
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM users LIMIT 1")
                row = cur.fetchone()
            if row:
                save_incident(row[0], diagnosis_event)
        finally:
            put_conn(conn)
    except Exception as e:
        log("error", "failed to save incident to db", error=str(e))


async def process_incident(incident: dict, producer: KafkaProducer) -> None:
    trace_id = new_trace_id()
    set_trace_id(trace_id)

    log("info", "processing incident",
        service=incident["service"],
        reason=incident.get("reason"))

    started_at = datetime.now(timezone.utc)

    agent_results = await asyncio.gather(
        _call_agent_with_retry(log_analyst.run, incident),
        _call_agent_with_retry(deploy_correlator.run, incident),
        _call_agent_with_retry(metrics_analyst.run, incident),
    )

    latency_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    resolution = resolve(list(agent_results), incident["service"])

    diagnosis_event = {
        "trace_id": trace_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": incident["service"],
        "incident_timestamp": incident["timestamp"],
        "latency_ms": latency_ms,
        "agent_results": list(agent_results),
        "resolution": resolution,
    }

    # Publish to Kafka.
    producer.send(TOPIC_DIAGNOSES, value=json.dumps(diagnosis_event).encode())
    producer.flush()

    # Save to Postgres, notify Slack, broadcast to dashboard.
    await asyncio.gather(
        _save_to_db(diagnosis_event),
        _notify_slack(diagnosis_event),
        manager.broadcast(diagnosis_event),
    )

    log("info", "diagnosis complete",
        service=incident["service"],
        latency_ms=latency_ms,
        disagreement_score=resolution["disagreement_score"])

    recent_diagnoses.append(diagnosis_event)
    if len(recent_diagnoses) > MAX_RECENT:
        recent_diagnoses.pop(0)


async def consume_loop(producer: KafkaProducer) -> None:
    log("info", "consume loop started")
    while True:
        incident = await incident_queue.get()
        await process_incident(incident, producer)