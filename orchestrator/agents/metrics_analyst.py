"""
agents/metrics_analyst.py - Metrics Analyst Agent

Looks at the quantitative signals in the incident (error rate, latency,
sample count) and identifies metric-level patterns. Where the Log Analyst
reads text-based signals and the Deploy Correlator checks deployment timing,
this agent focuses purely on the numbers.

Key interview point: three agents, three independent lenses on the same
incident. The resolver's job is to reconcile when they disagree.
"""

import asyncio
import json

from google import genai
from agents.base import call_gemini_with_backoff
from google.genai import types

from config import GEMINI_API_KEY
from logger import log

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "You are a senior SRE specializing in metrics-based incident analysis. "
    "Always respond with valid JSON only. No markdown, no code fences, no extra text."
)


def _classify_severity(avg_error_rate: float, avg_latency_ms: float) -> str:
    """Simple rule-based severity classification before we even call Gemini.
    This gives the agent concrete context and is also an easy interview talking
    point: 'we pre-classify severity in code so the LLM prompt has structured
    context rather than raw numbers.'"""
    if avg_error_rate > 0.30 or avg_latency_ms > 1500:
        return "critical"
    elif avg_error_rate > 0.15 or avg_latency_ms > 800:
        return "high"
    elif avg_error_rate > 0.10 or avg_latency_ms > 400:
        return "medium"
    return "low"


def _build_prompt(incident: dict, severity: str) -> str:
    return f"""Metric anomaly details:

Service: {incident["service"]}
Detected at: {incident["timestamp"]}
Pre-classified severity: {severity}

Metrics (averaged over last {incident.get("window_seconds", 10)}s):
  - Error rate: {incident["avg_error_rate"] * 100:.1f}% (threshold: 10%)
  - Avg latency: {incident["avg_latency_ms"]:.0f}ms
  - Error log count: {incident["error_log_count"]}
  - Sample count in window: {incident.get("sample_count", "unknown")}

Analyze the metric patterns and determine the most likely category of issue.
Respond with JSON in this exact format:

{{
  "root_cause": "one sentence describing what the metrics suggest",
  "confidence": "high or medium or low",
  "evidence": ["metric observation 1", "metric observation 2"],
  "recommended_action": "one concrete next step based on the metrics"
}}"""


async def run(incident: dict) -> dict:
    log("info", "metrics_analyst started", service=incident["service"])

    severity = _classify_severity(
        incident["avg_error_rate"],
        incident["avg_latency_ms"],
    )

    prompt = _build_prompt(incident, severity)

    def call_gemini():
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
            ),
        )
        return response.text

    raw_text = await call_gemini_with_backoff(call_gemini)
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        diagnosis = json.loads(cleaned)
    except json.JSONDecodeError:
        log("warn", "metrics_analyst got non-JSON response", service=incident["service"])
        diagnosis = {
            "root_cause": cleaned,
            "confidence": "low",
            "evidence": [],
            "recommended_action": "Manual review required",
        }

    log("info", "metrics_analyst completed",
        service=incident["service"],
        severity=severity,
        confidence=diagnosis.get("confidence"))

    return {
        "agent": "metrics_analyst",
        "diagnosis": diagnosis,
        "pre_classified_severity": severity,
    }