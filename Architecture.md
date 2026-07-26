# Real-Time Multi-Agent Incident Response Platform
## Architecture & Design Document

---

## What It Does

A distributed SaaS platform that monitors infrastructure in real time,
detects anomalies using stream processing, and fans out to three
independent AI agents to diagnose root causes — all with measurable
latency, accuracy, and agent disagreement metrics delivered to Slack
before an engineer opens a dashboard.

**Interview framing:** This is a distributed systems project that uses
LLMs as one component. The interesting engineering is in the stream
processing pipeline, async concurrency model, trace propagation,
evaluation harness, and SaaS architecture — not the prompts.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DATA SOURCES                          │
│  Prometheus metrics  │  GitHub webhooks  │  Log streams │
└──────────┬───────────┴────────┬──────────┴──────────────┘
           │                    │
           ▼                    ▼
┌──────────────────┐   ┌─────────────────────┐
│  Prometheus      │   │  GitHub Webhook      │
│  Poller          │   │  Handler (FastAPI)   │
│  (every 15s)     │   │  ngrok tunnel        │
└────────┬─────────┘   └──────────┬──────────┘
         │                         │
         ▼                         ▼
┌─────────────────────────────────────────────┐
│              KAFKA (KRaft mode)              │
│   topics: logs │ metrics │ deploys           │
│            │ incidents │ diagnoses           │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│         ANOMALY DETECTOR                  │
│  Hand-rolled hopping window               │
│  window=30s, slide=5s, threshold=10%      │
│  consumer.poll() timer-based evaluation   │
│  No LLM — pure Python, fast hot path      │
└──────────────────┬───────────────────────┘
                   │ incident event
                   ▼
┌──────────────────────────────────────────────────────┐
│              ORCHESTRATOR (FastAPI + asyncio)         │
│                                                       │
│  assigns trace_id via contextvars                     │
│                                                       │
│  asyncio.gather() ──────────────────────────────┐    │
│       │                                          │    │
│       ├──► Log Analyst Agent      (Gemini)       │    │
│       ├──► Deploy Correlator Agent (Gemini)      │    │
│       └──► Metrics Analyst Agent  (Gemini)  ◄───┘    │
│                                                       │
│  Semaphore (max 2 concurrent Gemini calls)            │
│  Circuit breaker (opens after 5 failures)             │
│  Timeout + exponential backoff retry per agent        │
│                                                       │
│                    │                                  │
│                    ▼                                  │
│              RESOLVER                                 │
│  Naive consensus + Jaccard disagreement score         │
│  Flags high disagreement (score > 0.6)                │
└──────────────────────────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        ▼          ▼          ▼
   Kafka       Slack       Neon
 diagnoses  notification  (Postgres)
   topic    to channel    incidents
                          table
        │
        ▼
┌──────────────────────┐
│   React Dashboard    │
│   WebSocket live     │
│   agent traces       │
└──────────────────────┘
```

---

## Key Design Decisions

### 1. Hot path / cold path separation

The anomaly detector (hot path) runs with no LLM — pure Python
consumer with hand-rolled hopping window logic. It detects threshold
breaches in 5-30 seconds and publishes structured incidents to Kafka.

The agents (cold path) run asynchronously, decoupled from detection
via Kafka. If Gemini is slow or the orchestrator restarts, incidents
queue in Kafka rather than being dropped. The consumer group offset
tracks exactly where processing left off.

**Interview answer for "why Kafka between detector and orchestrator?"**
Decouples detection rate from processing rate. Slow LLM responses
never block anomaly detection. Consumer group semantics give us
at-least-once delivery with offset tracking.

### 2. Hand-rolled agent orchestration (deliberately no LangGraph/CrewAI)

Using a framework would hide the mechanics. The orchestration is
plain asyncio:
- `asyncio.gather()` for concurrent fan-out
- `asyncio.wait_for()` for per-agent timeouts
- Exponential backoff retry (2s, 4s)
- Structured error returns — pipeline never crashes
- `asyncio.Semaphore(2)` limiting concurrent Gemini calls
- Circuit breaker opening after 5 consecutive failures

**Interview answer for "what happens if one agent times out?"**
`asyncio.wait_for()` cancels that coroutine after N seconds and
returns a structured `{"confidence": "none", "error": "timed out"}`
dict. `asyncio.gather()` still collects all three results. The
resolver handles partial results gracefully.

### 3. Hopping window anomaly detection

Window: 30 seconds. Slide interval: 5 seconds. 50% overlap.

Uses `consumer.poll(timeout_ms=1000)` instead of blocking
`for message in consumer` — this ensures windows are evaluated
on a timer even when Prometheus metrics arrive infrequently
(every 15 seconds). Critical fix for Prometheus-sourced metrics
vs the original simulator which sent continuously.

**Interview answer for "how do you handle infrequent metrics?"**
Changed from iterator-based consumer (blocks until message arrives)
to poll-based consumer with 1s timeout. Evaluation runs every
SLIDE_SECONDS regardless of message arrival rate.

### 4. Trace ID propagation via contextvars

Every incident is assigned a trace_id the moment it's dequeued.
`contextvars.ContextVar` propagates it through the entire async
call chain without passing it as a function argument. Every
structured log line carries the same trace_id.

**Interview answer for "how does trace ID survive asyncio.gather()?"**
`ContextVar` copies the current context into each new async task
automatically. The trace_id set before `asyncio.gather()` is
visible inside all three agent coroutines without any extra plumbing.

### 5. Resolver disagreement metric

Pairwise Jaccard similarity between keyword sets from each agent's
`root_cause` string. Score of 0.0 = full agreement, 1.0 = total
disagreement.

In practice scores are high (~0.85-0.93) even when agents converge
on the same problem, because they use different vocabulary.

**Honest limitation:** Keyword Jaccard underestimates semantic
agreement. The right fix is embedding-based similarity — noted as
a future improvement. High disagreement rate (100% > 0.6 threshold)
reflects this limitation, not actual agent confusion.

### 6. Session persistence for deploy correlation

Deploy events from GitHub webhooks are stored in Postgres (`deploys`
table) and loaded into the correlator cache on startup. This ensures
deploy correlation works correctly after orchestrator restarts —
a commit pushed before restart is still findable when a service
breaks after restart.

### 7. SaaS multi-tenancy foundation

- API key authentication with bcrypt password hashing
- Per-user integration configs stored in Postgres
- Prometheus poller spawns one asyncio task per user
- Slack notifications routed to each user's configured channel
- Neon (serverless Postgres) for zero-ops database management

---

## Evaluation Harness

The synthetic simulator writes `ground_truth.jsonl` recording the
true root cause of every injected incident. The eval harness
(`eval.py`) consumes the `diagnoses` Kafka topic and computes:

- **Accuracy**: keyword matching against known root cause categories
- **Latency percentiles**: p50/p95/p99 from incident detection to
  diagnosis published
- **Disagreement rate**: % of incidents with score > 0.6
- **Confidence distribution**: high / medium / low / none

---

## Measured Performance

| Metric | Value | Notes |
|---|---|---|
| End-to-end latency p50 | 16,871ms | Dominated by Gemini API latency |
| End-to-end latency p95 | 22,550ms | Rate limiting adds tail latency |
| End-to-end latency min | 13,889ms | Best case — no rate limiting |
| Agent confidence (high) | 100% | All diagnoses high confidence |
| Mean disagreement score | 0.902 | Expected — keyword Jaccard is strict |
| High disagreement rate | 100% | Threshold 0.6 — vocabulary mismatch |
| Load test throughput | 20/20 incidents | No drops under 3s inter-arrival |

## Latency Breakdown

| Component | Latency |
|---|---|
| Prometheus poll → Kafka | ~15s (configurable poll interval) |
| Kafka → detector window | 5-30s (hopping window) |
| Detector → orchestrator | <1s (Kafka consumer) |
| Agent fan-out (concurrent) | 7-22s (Gemini API, rate limited) |
| Resolver | <10ms |
| Slack notification | ~500ms |
| WebSocket broadcast | <5ms |

---

## Honest Limitations

| Limitation | Production fix |
|---|---|
| High Gemini latency | Paid tier or self-hosted LLM (Ollama) |
| Keyword disagreement scoring | Embedding-based semantic similarity |
| Single Kafka consumer | Multiple replicas in consumer group |
| Keyword accuracy matching | LLM-based semantic evaluation |
| No exactly-once processing | Flink or Kafka Streams |
| ngrok for GitHub webhooks | Static server with public IP |
| Free tier Gemini 5 req/min | Semaphore + circuit breaker mitigates |

---

## What I Would Do Differently at Production Scale

1. **Replace Python windowing with Flink.** Native watermarking,
   exactly-once semantics, horizontal scaling with no code changes.

2. **Embedding-based disagreement scoring.** Sentence embeddings
   give semantic similarity rather than keyword overlap.

3. **Persistent trace storage.** Ship structured logs to Jaeger or
   Tempo for cross-incident historical analysis.

4. **Kafka consumer group scaling.** Multiple orchestrator replicas
   in the same consumer group — already compatible since no shared
   mutable state between incidents.

5. **Dead letter queue.** Failed diagnoses currently logged but lost.
   A DLQ topic enables replay after agent recovery.

6. **Self-hosted LLM.** Replace Gemini free tier with Ollama running
   Llama 3 or Mistral locally — eliminates rate limits and API costs
   at scale.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Message broker | Kafka (KRaft, no ZooKeeper) | Decouples hot/cold path |
| Anomaly detection | Python + deque (hopping window) | Simple, explainable |
| Orchestrator | FastAPI + asyncio | Async fan-out, clean timeout/retry |
| Agents | Gemini 2.0 Flash via google-genai | Structured JSON output |
| Agent orchestration | Hand-rolled asyncio.gather() | Demonstrates mechanics |
| Trace propagation | Python contextvars | Per-task ambient context |
| Database | Neon (serverless Postgres) | Zero-ops, production-grade |
| Dashboard | React + Vite + WebSocket | Live agent reasoning traces |
| Auth | API key + bcrypt password | Simple, secure for v1 |
| Notifications | Slack Block Kit | Primary user touchpoint |
| Metrics source | Prometheus + custom poller | Real infrastructure metrics |
| Deploy tracking | GitHub webhooks + ngrok | Real deploy correlation |
| Evaluation | Custom harness vs ground truth | Objective accuracy measurement |

---

## Repository Structure

```
incident-response-platform/
  docker-compose.yml          # Kafka + Postgres + all services
  ARCHITECTURE.md             # This document
  README.md                   # Quickstart guide
  simulator/
    simulator.py              # Synthetic infra simulator
    detector.py               # Hopping window anomaly detector
    load_test.py              # Burst load tester
    kafka_utils.py            # Shared Kafka helpers
  orchestrator/
    main.py                   # FastAPI app + lifespan
    consumer.py               # Kafka consumer + agent fan-out
    trace.py                  # contextvars trace ID
    logger.py                 # Structured JSON logging
    config.py                 # Environment variables
    websocket_manager.py      # WebSocket broadcast manager
    agents/
      log_analyst.py          # Log pattern agent
      deploy_correlator.py    # Deploy timing agent
      metrics_analyst.py      # Metric pattern agent
      resolver.py             # Consensus + disagreement scoring
      base.py                 # Gemini helper + circuit breaker
    integrations/
      slack.py                # Slack Block Kit notifications
      prometheus.py           # Prometheus metrics poller
      github.py               # GitHub webhook receiver
    db/
      connection.py           # Neon/Postgres connection pool
      models.py               # Users, integrations, incidents, deploys
    routers/
      auth.py                 # Signup, login, API key auth
      integrations.py         # Connect Slack/Prometheus/GitHub
      incidents.py            # Incident history REST API
  dashboard/
    src/
      pages/
        Landing.jsx           # Marketing landing page
        Signup.jsx            # Account creation
        Login.jsx             # Email/password login
        Onboarding.jsx        # Integration wizard
        Dashboard.jsx         # Live incident feed
      components/
        Navbar.jsx            # Shared navigation
        IncidentCard.jsx      # Incident with agent traces
        AgentResult.jsx       # Individual agent reasoning
        StatsBar.jsx          # Aggregate metrics
      theme/
        ThemeContext.jsx      # Dark/light theme switching
  demo-app/
    services/app.py           # Fake microservices with /break /fix
    prometheus.yml            # Prometheus scrape config
    demo.py                   # Interactive demo controller
```