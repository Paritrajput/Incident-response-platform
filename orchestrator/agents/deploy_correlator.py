"""
agents/deploy_correlator.py - Deploy Correlator Agent

Checks whether a recent bad deploy caused this incident.
In a real system this would query a deployment database or git history.
Here we consume from the `deploys` Kafka topic (via a small in-memory
cache populated at startup) to find deploys that happened close in time
to the incident.

Key interview point: this agent has its own data source (deploy history)
that the other agents don't have. That's why we run all three in parallel
rather than sequentially - each brings independent signal.
"""

import asyncio
import json
from datetime import datetime, timezone
from collections import deque

from google import genai
from agents.base import call_gemini_with_backoff
from google.genai import types

from config import GEMINI_API_KEY
from logger import log

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "You are a senior SRE investigating whether a recent deployment caused a production incident. "
    "Always respond with valid JSON only. No markdown, no code fences, no extra text."
)

# In-memory cache of recent deploy events, populated by the consumer thread.
# A deque with maxlen automatically drops old entries - simple sliding window.
recent_deploys: deque = deque(maxlen=50)


def record_deploy(deploy_event: dict) -> None:
    """Called by the Kafka consumer thread to cache deploy events as they arrive."""
    recent_deploys.append(deploy_event)


def _find_related_deploys(incident: dict) -> list:
    """
    Find deploys for the same application and service
    that happened within five minutes before the incident.
    """

    incident_time = datetime.fromisoformat(
        incident["timestamp"]
    )

    related = []

    for deploy in recent_deploys:

        # Must belong to the same application
        if deploy.get("application_id") != incident.get("application_id"):
            continue

        # Must be the same service
        if deploy.get("service") != incident["service"]:
            continue

        deploy_time = datetime.fromisoformat(
            deploy["timestamp"]
        )

        seconds_before = (
            incident_time - deploy_time
        ).total_seconds()

        if 0 <= seconds_before <= 300:

            related.append({
                "deploy_id": deploy["deploy_id"],
                "commit_message": deploy["commit_message"],
                "seconds_before_incident": int(seconds_before),
            })

    return related


def _build_prompt(incident: dict, related_deploys: list) -> str:
    if related_deploys:
        deploy_text = "\n".join(
            f"  - deploy_id={d['deploy_id']}, "
            f"commit='{d['commit_message']}', "
            f"{d['seconds_before_incident']}s before incident"
            for d in related_deploys
        )
    else:
        deploy_text = "  No deploys found for this service in the 5 minutes before the incident."

    return f"""Incident details:

Service: {incident["service"]}
Incident time: {incident["timestamp"]}
Error rate: {incident["avg_error_rate"] * 100:.1f}%
Latency: {incident["avg_latency_ms"]:.0f}ms

Recent deploys for this service (last 5 minutes before incident):
{deploy_text}

Based on deploy timing and commit messages, assess whether a bad deploy
is the likely cause. Respond with JSON in this exact format:

{{
  "root_cause": "one sentence - was this deploy-related or not?",
  "confidence": "high or medium or low",
  "evidence": ["observation 1", "observation 2"],
  "recommended_action": "one concrete next step"
}}"""


async def run(incident: dict) -> dict:
    log(
    "info",
    "deploy_correlator started",
    application_id=incident.get("application_id"),
    service=incident["service"],
)

    related_deploys = _find_related_deploys(incident)
    log(
        "info",
        "deploy_correlator found related deploys",
        application_id=incident.get("application_id"),
        service=incident["service"],
        count=len(related_deploys),
    )

    prompt = _build_prompt(incident, related_deploys)

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
        log("warn", "deploy_correlator got non-JSON response", service=incident["service"])
        diagnosis = {
            "root_cause": cleaned,
            "confidence": "low",
            "evidence": [],
            "recommended_action": "Manual review required",
        }

    log(
        "info",
        "deploy_correlator completed",
        application_id=incident.get("application_id"),
        service=incident["service"],
        confidence=diagnosis.get("confidence"),
    )

    return {
        "agent": "deploy_correlator",
        "diagnosis": diagnosis,
        "deploy_count_found": len(related_deploys),
    }