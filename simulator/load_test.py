"""
load_test.py - Burst load tester for the incident pipeline.

Injects N incidents in rapid succession to observe:
- Whether the orchestrator queues and processes all of them
- How latency degrades under concurrent load
- Whether Kafka consumer group rebalancing causes any dropped messages

This is NOT a production-grade load test - it's designed to generate
honest, specific numbers and failure observations to talk about in interviews.

Run with:
    python load_test.py --incidents 20 --delay 0.5
"""

import argparse
import json
import time
import uuid
from datetime import datetime, timezone

from kafka_utils import make_producer, TOPIC_INCIDENTS


def make_synthetic_incident(service: str) -> dict:
    """
    Directly inject a pre-formed incident (bypassing the detector).
    This lets us control burst rate precisely without waiting for the
    sliding window to fire.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": service,
        "reason": "error_rate_threshold_breach",
        "threshold": 0.10,
        "avg_error_rate": round(0.15 + (hash(service) % 20) / 100, 3),
        "avg_latency_ms": 900 + (hash(service) % 500),
        "error_log_count": 5,
        "sample_log_messages": [
            "connection timeout to downstream",
            "database query failed",
            "unhandled exception in request handler",
        ],
        "window_seconds": 10,
        "sample_count": 9,
        "_load_test_id": str(uuid.uuid4())[:8],
    }


SERVICES = ["checkout-service", "auth-service", "payment-service", "inventory-service"]


def run(num_incidents: int, delay_seconds: float):
    producer = make_producer()
    print(f"\n[LOAD TEST] Injecting {num_incidents} incidents "
          f"with {delay_seconds}s delay between each")
    print(f"[LOAD TEST] Started at {datetime.now().strftime('%H:%M:%S')}\n")

    sent = []
    for i in range(num_incidents):
        service = SERVICES[i % len(SERVICES)]
        incident = make_synthetic_incident(service)
        producer.send(TOPIC_INCIDENTS, value=incident)
        producer.flush()

        sent.append({
            "index": i + 1,
            "service": service,
            "load_test_id": incident["_load_test_id"],
            "sent_at": time.time(),
        })

        print(f"  [{i+1:02d}/{num_incidents}] → {service} "
              f"(id={incident['_load_test_id']})")

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    print(f"\n[LOAD TEST] All {num_incidents} incidents sent.")
    print(f"[LOAD TEST] Watch the orchestrator logs and /status endpoint.")
    print(f"[LOAD TEST] Expected processing time: "
          f"~{int(num_incidents * 7 / 1)}s if sequential, "
          f"~{7 + int(num_incidents * delay_seconds)}s if properly queued.\n")

    # Save sent log for comparison against diagnoses later.
    with open("load_test_sent.json", "w") as f:
        json.dump(sent, f, indent=2)
    print(f"[LOAD TEST] Sent log saved to load_test_sent.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--incidents", type=int, default=10,
                        help="Number of incidents to inject (default: 10)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds between each incident (default: 1.0, use 0 for burst)")
    args = parser.parse_args()
    run(args.incidents, args.delay)