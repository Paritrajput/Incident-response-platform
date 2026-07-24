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
    metrics_by_service = {}

    async with httpx.AsyncClient(timeout=10) as client:
        # Query error rate - use label_replace to ensure service label exists
        try:
            resp = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": "service_error_rate"}
            )
            data = resp.json().get("data", {}).get("result", [])
            print(f"[PROMETHEUS] error_rate results: {len(data)} series", flush=True)
            for r in data:
                # service label lives inside the metric labels
                svc = (
                    r["metric"].get("service") or
                    r["metric"].get("instance", "unknown").split(":")[0]
                )
                value = float(r["value"][1])
                print(f"[PROMETHEUS] found service={svc} error_rate={value} labels={r['metric']}", flush=True)
                metrics_by_service.setdefault(svc, {})["error_rate"] = value
        except Exception as e:
            print(f"[PROMETHEUS] error_rate query failed: {e}", flush=True)

        # Query latency
        try:
            resp = await client.get(
                f"{prometheus_url}/api/v1/query",
                params={"query": "http_request_duration_seconds * 1000"}
            )
            for r in resp.json().get("data", {}).get("result", []):
                svc = (
                    r["metric"].get("service") or
                    r["metric"].get("instance", "unknown").split(":")[0]
                )
                value = float(r["value"][1])
                metrics_by_service.setdefault(svc, {})["latency_ms"] = value
        except Exception as e:
            print(f"[PROMETHEUS] latency query failed: {e}", flush=True)

    print(f"[PROMETHEUS] services found: {list(metrics_by_service.keys())}", flush=True)

    events = []
    for svc, data in metrics_by_service.items():
        if svc == "unknown":
            continue  # skip entries where we couldn't identify the service
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