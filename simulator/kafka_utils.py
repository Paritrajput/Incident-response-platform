"""
Small helper so every script connects to Kafka the same way.
Keeping this in one place means if the broker address changes,
we only update it here.
"""

import json
from kafka import KafkaProducer

KAFKA_BROKER = "localhost:9092"

TOPIC_LOGS = "logs"
TOPIC_METRICS = "metrics"
TOPIC_DEPLOYS = "deploys"
TOPIC_INCIDENTS = "incidents"
TOPIC_DIAGNOSES = "diagnoses"


def make_producer():
    """Create a Kafka producer that automatically converts Python dicts to JSON bytes."""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )