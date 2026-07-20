"""
integrations/prometheus.py

Polls Prometheus every 30s. Uses the exact metric names exposed
by the demo-app services (service_error_rate, http_request_duration_seconds).
"""

import asyncio
import json
from datetime import datetime, timezone

import httpx
from logger import log

POLL_INTERVAL = 15  # poll every 15s for snappier demo

# PromQL queries matching demo-app metric names.
# These also work with standard kube-state-metrics if user has real k8s.
ERROR_RATE_QUERY = 'service_error_rate'
LATENCY_QUERY = 'http_request_duration_seconds * 1000'   # convert s → ms


async def poll_once(prometheus_url: str) -> list[dict]:
    """Query Prometheus and return metric events per service."""
    metrics_by_service = {}

    async with httpx.AsyncClient(timeout=10) as client:
        # Error rate
        try:
            resp = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": ERROR_RATE_QUERY}
            )
            for r in resp.json().get("data", {}).get("result", []):
                svc = r["metric"].get("service", "unknown")
                metrics_by_service.setdefault(svc, {})["error_rate"] = float(r["value"][1])
        except Exception as e:
            log("warn", "prometheus error_rate query failed", error=str(e))

        # Latency
        try:
            resp = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": LATENCY_QUERY}
            )
            for r in resp.json().get("data", {}).get("result", []):
                svc = r["metric"].get("service", "unknown")
                metrics_by_service.setdefault(svc, {})["latency_ms"] = float(r["value"][1])
        except Exception as e:
            log("warn", "prometheus latency query failed", error=str(e))

    events = []
    for svc, data in metrics_by_service.items():
        events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": svc,
            "error_rate": round(data.get("error_rate", 0.0), 4),
            "latency_ms": int(data.get("latency_ms", 0)),
            "source": "prometheus",
        })
    return events


async def run_poller(user_id: int, config: dict, producer):
    prometheus_url = config.get("prometheus_url", "").rstrip("/")
    log("info", "prometheus poller started", user_id=user_id, url=prometheus_url)

    while True:
        try:
            events = await poll_once(prometheus_url)
            for event in events:
                producer.send("metrics", value=json.dumps(event).encode())
            if events:
                producer.flush()
                log("info", "prometheus polled", user_id=user_id, services=len(events))
        except Exception as e:
            log("error", "prometheus poll error", user_id=user_id, error=str(e))

        await asyncio.sleep(POLL_INTERVAL)