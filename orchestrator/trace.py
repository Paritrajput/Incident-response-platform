"""
trace.py - Trace ID propagation using Python's contextvars.

The key problem this solves: when we fan out to 3 agents concurrently
with asyncio.gather(), each runs in its own async task. We want every
log line from every agent to carry the same trace_id as the incident
that triggered it, so we can grep logs and see the full story.

contextvars.ContextVar is designed exactly for this: it's like a
thread-local variable but for async tasks. When you copy a context
(copy_context()) and run something in it, changes to the var inside
that task don't leak back to the parent - but the parent's value IS
visible to children at the point they start.

Usage:
    set_trace_id("abc123")       # set for the current async task
    get_trace_id()               # read it anywhere in the call stack
"""

import uuid
from contextvars import ContextVar

# The ContextVar that holds the trace ID for the current async task.
# Default is "no-trace" so logs before any incident is set are still valid.
_trace_id: ContextVar[str] = ContextVar("trace_id", default="no-trace")


def set_trace_id(trace_id: str) -> None:
    _trace_id.set(trace_id)


def get_trace_id() -> str:
    return _trace_id.get()


def new_trace_id() -> str:
    """Generate a short, readable trace ID."""
    return str(uuid.uuid4())[:8]