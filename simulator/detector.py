"""
Anomaly Detector (hand-rolled sliding window)

Consumes from `logs` and `metrics`, keeps a rolling window of recent
readings per service, and every SLIDE_SECONDS recomputes aggregates
over the last WINDOW_SECONDS of data. If a service's windowed error
rate crosses a threshold, we emit an incident.

Key fix: uses consumer_timeout_ms so the evaluation loop runs on a
fixed timer rather than waiting for messages. This ensures all services
are evaluated even when messages arrive infrequently (e.g. Prometheus
polling every 15 seconds).
"""

import json
import time
from collections import deque, defaultdict
from datetime import datetime, timezone

from kafka import KafkaConsumer
from kafka.errors import KafkaError

from kafka_utils import make_producer, KAFKA_BROKER, TOPIC_LOGS, TOPIC_METRICS, TOPIC_INCIDENTS

WINDOW_SECONDS = 30   # wider window to catch Prometheus metrics (polls every 15s)
SLIDE_SECONDS = 5
# Prometheus reports error rates as percentages: 10 represents 10%.
ERROR_RATE_THRESHOLD = 10


metric_buffers = defaultdict(deque)
log_buffers = defaultdict(deque)
open_incidents = set()


def now_ts():
    return time.time()


def make_consumer():
    return KafkaConsumer(
        TOPIC_LOGS,
        TOPIC_METRICS,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="latest",
        group_id="anomaly-detector-v2",  # new group ID so offsets reset cleanly
        consumer_timeout_ms=1000,  # don't block forever - return after 1s with no messages
    )


def add_to_buffer(buffer, key, value):
    buffer[key].append((now_ts(), value))


def trim_old_entries(buffer, key):
    cutoff = now_ts() - WINDOW_SECONDS
    while buffer[key] and buffer[key][0][0] < cutoff:
        buffer[key].popleft()


def compute_window_stats(key):
    trim_old_entries(metric_buffers, key)
    trim_old_entries(log_buffers, key)

    metrics = [v for _, v in metric_buffers[key]]
    logs = [v for _, v in log_buffers[key]]

    if not metrics:
        return None

    avg_error_rate = sum(m["error_rate"] for m in metrics) / len(metrics)
    avg_latency_ms = sum(m["latency_ms"] for m in metrics) / len(metrics)
    error_log_count = sum(1 for l in logs if l.get("level") == "ERROR")
    application_id = metrics[0]["application_id"]

    return {
        "application_id": application_id,
        "avg_error_rate": round(avg_error_rate, 4),
        "avg_latency_ms": round(avg_latency_ms, 1),
        "error_log_count": error_log_count,
        "sample_log_messages": [l["message"] for l in logs if l.get("level") == "ERROR"][:3],
        "window_seconds": WINDOW_SECONDS,
        "sample_count": len(metrics),
    }


def emit_incident(producer, service, stats):
    print("STATS:", stats, flush=True)
    incident = {
        "application_id": stats["application_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": service,
        "reason": "error_rate_threshold_breach",
        "threshold": ERROR_RATE_THRESHOLD,
        **stats,
    }
    print("INCIDENT TO SEND:", incident, flush=True)
    producer.send(TOPIC_INCIDENTS, value=incident)
    print(f"[INCIDENT EMITTED] {service} -> error_rate={stats['avg_error_rate']}")


def check_recovery(key, stats):
    if key in open_incidents and stats["avg_error_rate"] < ERROR_RATE_THRESHOLD:
        open_incidents.remove(key)
        print(f"[RECOVERED] {key}")


def evaluate_all_services(producer):
    all_services = set(metric_buffers.keys()) | set(log_buffers.keys())
    if not all_services:
        return

  
    for key in all_services:

        application_id, service = key

        stats = compute_window_stats(key)

        if stats is None:
            continue

        if stats["avg_error_rate"] >= ERROR_RATE_THRESHOLD:

            if key not in open_incidents:

                emit_incident(producer, service, stats)

                open_incidents.add(key)

        else:

            check_recovery(key, stats)

def main():
    producer = make_producer()
    consumer = make_consumer()  # create ONCE here
    print(f"Detector started. window={WINDOW_SECONDS}s slide={SLIDE_SECONDS}s "
          f"threshold={ERROR_RATE_THRESHOLD}")

    last_eval = now_ts()

    while True:
        # Poll for messages with timeout - returns empty dict if no messages
        records = consumer.poll(timeout_ms=1000)

        for topic_partition, messages in records.items():
            for message in messages:
                value = message.value
                application_id = value.get("application_id")
                service = value.get("service")

                key = (application_id, service)
                if not service:
                    continue

                if message.topic == TOPIC_METRICS:
                    print("METRIC RECEIVED:", value, flush=True)
                    add_to_buffer(metric_buffers, key, value)
                elif message.topic == TOPIC_LOGS:
                    add_to_buffer(log_buffers, key, value)

        # Always evaluate every SLIDE_SECONDS regardless of message arrival
        if now_ts() - last_eval >= SLIDE_SECONDS:
            evaluate_all_services(producer)
            producer.flush()
            last_eval = now_ts()


if __name__ == "__main__":
    main()
