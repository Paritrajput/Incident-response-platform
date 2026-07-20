"""
agents/log_analyst.py - Log Analyst Agent

Receives a structured incident (from the detector) and asks Gemini to
identify the root cause from the log messages and metrics. Returns a
structured diagnosis dict, not raw LLM text.

The agent is a plain async function - not a class, not a framework.
This makes it easy to test, easy to explain, and easy to swap the
underlying LLM if needed.
"""

import asyncio
import json

from google import genai
from agents.base import call_gemini_with_backoff
from google.genai import types

from config import GEMINI_API_KEY
from logger import log

# Configure Gemini once when this module is first imported.
# Same as JS: const ai = new GoogleGenAI({ apiKey: "..." })
client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "You are a senior SRE diagnosing production incidents. "
    "Always respond with valid JSON only. No markdown, no code fences, no extra text."
)


def _build_prompt(incident: dict) -> str:
    return f"""Here is the incident data from our monitoring system:

Service: {incident["service"]}
Detected at: {incident["timestamp"]}
Average error rate (last 10s): {incident["avg_error_rate"] * 100:.1f}%
Average latency (last 10s): {incident["avg_latency_ms"]:.0f}ms
Error log count in window: {incident["error_log_count"]}

Sample error log messages:
{chr(10).join(f"  - {m}" for m in incident.get("sample_log_messages", []))}

Provide a diagnosis as a JSON object in this exact format:

{{
  "root_cause": "one sentence describing the most likely root cause",
  "confidence": "high or medium or low",
  "evidence": ["key observation 1", "key observation 2"],
  "recommended_action": "one concrete next step an on-call engineer should take"
}}"""


async def run(incident: dict) -> dict:
    """
    Call Gemini with the incident context and return a structured diagnosis.

    Gemini's Python SDK is synchronous, so we use asyncio.to_thread() to
    run it in a thread pool without blocking the FastAPI event loop.

    Python equivalent of your JS pattern:
        ai.models.generateContent({ model, contents, config: { systemInstruction } })
    """
    log("info", "log_analyst started", service=incident["service"])

    prompt = _build_prompt(incident)

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

    # Strip markdown fences in case Gemini adds them despite instructions.
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        diagnosis = json.loads(cleaned)
    except json.JSONDecodeError:
        log("warn", "log_analyst got non-JSON response",
            service=incident["service"], raw=raw_text[:200])
        diagnosis = {
            "root_cause": cleaned,
            "confidence": "low",
            "evidence": [],
            "recommended_action": "Manual review required - agent returned unstructured output",
        }

    log("info", "log_analyst completed",
        service=incident["service"],
        confidence=diagnosis.get("confidence"))

    return {
        "agent": "log_analyst",
        "diagnosis": diagnosis,
    }