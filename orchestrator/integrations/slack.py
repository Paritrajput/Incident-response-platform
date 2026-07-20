"""
integrations/slack.py - Slack notification sender.

Sends a formatted diagnosis message to a Slack channel when an
incident is diagnosed. This is the primary user-facing output —
most users will see this before they ever open the dashboard.

Uses Slack's Block Kit for structured formatting (sections, buttons).
No SDK needed — plain HTTP to Slack's API.
"""

import asyncio
import httpx
from logger import log


async def send_diagnosis(
    bot_token: str,
    channel_id: str,
    diagnosis_event: dict,
    dashboard_url: str = "http://localhost:3000",
) -> bool:
    """
    Send a formatted incident diagnosis to a Slack channel.
    Returns True on success, False on failure (never raises).
    """
    resolution = diagnosis_event.get("resolution", {})
    final = resolution.get("final_diagnosis", {})
    service = diagnosis_event.get("service", "unknown")
    trace_id = diagnosis_event.get("trace_id", "")
    latency_ms = diagnosis_event.get("latency_ms", 0)
    confidence = final.get("confidence", "unknown")
    disagreement = resolution.get("disagreement_score", 0)

    # Pick an emoji based on confidence.
    emoji = {"high": "🔴", "medium": "🟠", "low": "🟡"}.get(confidence, "⚪")

    # Format evidence bullets.
    evidence = final.get("evidence", [])
    evidence_text = "\n".join(f"• {e}" for e in evidence[:3]) or "No evidence recorded"

    # Slack Block Kit message.
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} Incident: {service}"}
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Confidence:*\n{confidence.title()}"},
                {"type": "mrkdwn", "text": f"*Latency:*\n{latency_ms}ms"},
                {"type": "mrkdwn", "text": f"*Trace ID:*\n`{trace_id}`"},
                {"type": "mrkdwn", "text": f"*Agent Disagreement:*\n{disagreement:.2f}"},
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Root Cause:*\n{final.get('root_cause', 'Unknown')}"
            }
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Evidence:*\n{evidence_text}"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommended Action:*\n{final.get('recommended_action', '—')}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Full Trace →"},
                    "url": f"{dashboard_url}?trace={trace_id}",
                    "style": "primary",
                }
            ]
        },
        {"type": "divider"},
    ]

    payload = {"channel": channel_id, "blocks": blocks}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {bot_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            data = response.json()
            if not data.get("ok"):
                log("error", "slack send failed", error=data.get("error"))
                return False

            log("info", "slack notification sent",
                service=service, channel=channel_id)
            return True

    except Exception as e:
        log("error", "slack send exception", error=str(e))
        return False