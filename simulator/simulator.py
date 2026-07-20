"""
Synthetic Infra Simulator

Generates fake logs, metrics, and deploy events for a handful of services,
and writes them to Kafka. Most of the time things look healthy ("normal mode").
Every so often, it injects a labeled incident (e.g. a bad deploy that causes
errors to spike) and records the ground truth to a local file so we can later
check whether our agents diagnosed it correctly.

Run it with:
    python simulator.py
"""

import json
import random
import time
import uuid
from datetime import datetime, timezone

from kafka_utils import make_producer, TOPIC_LOGS, TOPIC_METRICS, TOPIC_DEPLOYS

SERVICES = ["checkout-service", "auth-service", "payment-service", "inventory-service"]

# Where we record "what actually happened" so the eval harness can check
# agent diagnoses against reality later.
GROUND_TRUTH_FILE = "ground_truth.jsonl"

# If a service is "sick", we bias its logs/metrics towards errors.
# Empty dict = nothing is wrong right now.
sick_services = {}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def emit_log(producer, service):
    is_sick = service in sick_services
    # Sick services emit mostly ERROR/WARN logs, healthy ones mostly INFO.
    if is_sick:
        level = random.choices(["ERROR", "WARN", "INFO"], weights=[70, 20, 10])[0]
    else:
        level = random.choices(["INFO", "WARN", "ERROR"], weights=[90, 8, 2])[0]

    messages = {
        "ERROR": ["connection timeout to downstream", "unhandled exception in request handler", "database query failed"],
        "WARN": ["high response latency detected", "retrying failed request"],
        "INFO": ["request handled successfully", "health check passed"],
    }

    event = {
        "timestamp": now_iso(),
        "service": service,
        "level": level,
        "message": random.choice(messages[level]),
    }
    producer.send(TOPIC_LOGS, value=event)


def emit_metric(producer, service):
    is_sick = service in sick_services
    if is_sick:
        error_rate = round(random.uniform(0.15, 0.40), 3)   # 15-40% errors = clearly unhealthy
        latency_ms = random.randint(800, 2000)
    else:
        error_rate = round(random.uniform(0.0, 0.02), 3)    # 0-2% errors = healthy baseline
        latency_ms = random.randint(50, 200)

    event = {
        "timestamp": now_iso(),
        "service": service,
        "error_rate": error_rate,
        "latency_ms": latency_ms,
    }
    producer.send(TOPIC_METRICS, value=event)


def emit_deploy(producer, service, is_bad_deploy=False):
    event = {
        "timestamp": now_iso(),
        "service": service,
        "deploy_id": str(uuid.uuid4())[:8],
        "commit_message": "fix: refactor connection pooling" if is_bad_deploy else "chore: update dependencies",
        "is_bad_deploy_label": is_bad_deploy,  # ground truth label, agents should NOT see this field name as a hint in real use
    }
    producer.send(TOPIC_DEPLOYS, value=event)
    return event


def record_ground_truth(incident_id, service, root_cause, started_at):
    """Append the true cause of an incident to a local file for later evaluation."""
    record = {
        "incident_id": incident_id,
        "service": service,
        "root_cause": root_cause,
        "started_at": started_at,
    }
    with open(GROUND_TRUTH_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
    print(f"[GROUND TRUTH] {record}")


def inject_bad_deploy_incident(producer):
    """Scenario 1: a bad deploy causes a service to start erroring."""
    service = random.choice(SERVICES)
    incident_id = str(uuid.uuid4())[:8]
    started_at = now_iso()

    emit_deploy(producer, service, is_bad_deploy=True)
    sick_services[service] = {"incident_id": incident_id, "started_at": started_at}

    record_ground_truth(incident_id, service, "bad_deploy", started_at)
    print(f"[INCIDENT INJECTED] {service} is now sick due to bad deploy (incident_id={incident_id})")


def recover_services():
    """After some time, sick services go back to healthy (simulates a fix or rollback)."""
    sick_services.clear()


def main():
    producer = make_producer()
    print("Simulator started. Producing to topics: logs, metrics, deploys")
    print(f"Services: {SERVICES}")

    tick = 0
    incident_active_for = 0

    while True:
        for service in SERVICES:
            emit_log(producer, service)
            emit_metric(producer, service)

        # Occasionally a normal (healthy) deploy happens.
        if random.random() < 0.02:
            emit_deploy(producer, random.choice(SERVICES), is_bad_deploy=False)

        # Every ~30 seconds, maybe inject an incident if nothing is currently broken.
        if not sick_services and random.random() < 0.05:
            inject_bad_deploy_incident(producer)
            incident_active_for = 0

        # Keep the incident active for ~10 ticks (~10 seconds), then recover.
        if sick_services:
            incident_active_for += 1
            if incident_active_for > 10:
                print("[RECOVERY] services back to healthy")
                recover_services()

        producer.flush()
        tick += 1
        time.sleep(1)


if __name__ == "__main__":
    main()