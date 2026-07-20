"""
demo-app/services/app.py

A fake microservice that exposes REAL Prometheus metrics.
Run three instances on different ports to simulate a microservices stack.

Usage:
    python app.py --service payment-service --port 8001
    python app.py --service auth-service --port 8002
    python app.py --service checkout-service --port 8003

The /break and /fix endpoints let you trigger real metric spikes
on demand for demos — simulating a bad deploy causing errors.
"""

import argparse
import random
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ── State ────────────────────────────────────────────────────────────────────
# When broken=True, requests start failing and latency spikes.
state = {
    "broken": False,
    "requests_total": 0,
    "errors_total": 0,
    "service": "unknown",
}

# ── Metrics tracking ─────────────────────────────────────────────────────────
# We track these manually to produce Prometheus-format output.
request_count = {"total": 0, "errors": 0}
latency_sum = 0.0
latency_count = 0


def handle_request():
    """Simulate one request — returns (status_code, latency_ms)."""
    global latency_sum, latency_count

    if state["broken"]:
        # Broken: 25-40% error rate, high latency
        latency = random.uniform(800, 2500)
        is_error = random.random() < 0.70
    else:
        # Healthy: <2% error rate, normal latency
        latency = random.uniform(20, 150)
        is_error = random.random() < 0.01

    latency_sum += latency
    latency_count += 1
    request_count["total"] += 1
    if is_error:
        request_count["errors"] += 1

    return 500 if is_error else 200, latency


def background_traffic():
    """Generate constant background traffic so metrics are always moving."""
    while True:
        handle_request()
        time.sleep(random.uniform(0.1, 0.3))  # ~5 requests/sec


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        service = state["service"]

        if self.path == "/metrics":
            # Real Prometheus exposition format
            total = request_count["total"]
            errors = request_count["errors"]
            error_rate = errors / total if total > 0 else 0
            avg_latency = (latency_sum / latency_count / 1000) if latency_count > 0 else 0
            if state["broken"]:
                recent_total = max(request_count.get("recent_total", 1), 1)
                recent_errors = request_count.get("recent_errors", 0)
                error_rate = max(error_rate, recent_errors / recent_total)

            metrics = f"""# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{{service="{service}",status="200"}} {total - errors}
http_requests_total{{service="{service}",status="500"}} {errors}

# HELP http_request_duration_seconds Request latency
# TYPE http_request_duration_seconds gauge
http_request_duration_seconds{{service="{service}"}} {avg_latency:.4f}

# HELP service_error_rate Current error rate (0-1)
# TYPE service_error_rate gauge
service_error_rate{{service="{service}"}} {error_rate:.4f}

# HELP service_healthy 1=healthy 0=broken
# TYPE service_healthy gauge
service_healthy{{service="{service}"}} {0 if state["broken"] else 1}
"""
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(metrics.encode())

        elif self.path == "/break":
            # Trigger an incident - simulates a bad deploy
            state["broken"] = True
            request_count["total"] = 0
            request_count["errors"] = 0
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"{service} is now BROKEN (high error rate + latency)".encode())
            print(f"[{service}] 💥 BROKEN - errors will spike now")

        elif self.path == "/fix":
            # Simulate a rollback / fix
            state["broken"] = False
            request_count["total"] = 0
            request_count["errors"] = 0
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f"{service} is now HEALTHY".encode())
            print(f"[{service}] ✅ FIXED - back to normal")

        elif self.path == "/health":
            self.send_response(200 if not state["broken"] else 503)
            self.end_headers()
            self.wfile.write(b"ok" if not state["broken"] else b"unhealthy")

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # suppress default access logs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="demo-service")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    state["service"] = args.service

    # Start background traffic generator
    t = threading.Thread(target=background_traffic, daemon=True)
    t.start()

    print(f"[{args.service}] Running on port {args.port}")
    print(f"  Metrics:  http://localhost:{args.port}/metrics")
    print(f"  Break it: http://localhost:{args.port}/break")
    print(f"  Fix it:   http://localhost:{args.port}/fix")

    server = HTTPServer(("0.0.0.0", args.port), MetricsHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()