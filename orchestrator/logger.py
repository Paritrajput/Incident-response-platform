"""
logger.py - Structured logging that always includes the current trace_id.

Every log line is a JSON object, which means:
- Easy to grep/filter by trace_id, service, agent, etc.
- In a real system you'd ship these to Loki/Elasticsearch.
- For interviews: "all logs are structured JSON with trace ID propagated
  via contextvars across the async fan-out" is a clean, specific answer.

Usage:
    from logger import log
    log("info", "agent called", agent="log_analyst", service="payment-service")
"""

import json
import sys
from datetime import datetime, timezone

from trace import get_trace_id


def log(level: str, message: str, **kwargs) -> None:
    """
    Emit a structured JSON log line to stdout.

    level   : "info", "warn", "error"
    message : human-readable description
    kwargs  : any extra fields to include (agent, service, latency_ms, etc.)
    """
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "trace_id": get_trace_id(),  # automatically pulled from contextvars
        "message": message,
        **kwargs,
    }
    print(json.dumps(entry), file=sys.stdout, flush=True)