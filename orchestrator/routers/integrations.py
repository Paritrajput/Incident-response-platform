"""
routers/integrations.py - Connect/disconnect Slack, Prometheus, GitHub.

These endpoints are what the onboarding wizard calls when a user
pastes their Slack token or Prometheus URL. Config is saved to
Postgres and immediately available to the pollers and notifiers.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from db import models
# from routers.auth import get_current_user
from auth.dependencies import get_current_user

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ── Slack ────────────────────────────────────────────────────────────────────

class SlackConfig(BaseModel):
    bot_token: str       # xoxb-... from Slack app settings
    channel_id: str      # C... from Slack channel details


@router.post("/slack")
async def connect_slack(config: SlackConfig, user=Depends(get_current_user)):
    """Save Slack credentials for the current user."""
    result = models.upsert_integration(user["id"], "slack", config.model_dump())
    return {"status": "connected", "integration": result}


# ── Prometheus ───────────────────────────────────────────────────────────────

class PrometheusConfig(BaseModel):
    prometheus_url: str             
    error_rate_query: Optional[str] = None   # custom PromQL or use default
    latency_query: Optional[str] = None


@router.post("/prometheus")
async def connect_prometheus(config: PrometheusConfig, user=Depends(get_current_user)):
    """Save Prometheus config. The poller picks it up on next cycle."""
    result = models.upsert_integration(user["id"], "prometheus", config.model_dump())
    return {"status": "connected", "integration": result}


# ── GitHub ───────────────────────────────────────────────────────────────────

class GitHubConfig(BaseModel):
    webhook_secret: str     # secret you set in GitHub webhook settings
    repo_to_service: Optional[dict] = {}    # {"my-org/my-repo": "payment-service"}


@router.post("/github")
async def connect_github(config: GitHubConfig, user=Depends(get_current_user)):
    """
    Save GitHub webhook config.
    After calling this, set up the webhook in your GitHub repo:
      Settings → Webhooks → Add webhook
      URL: http://yourserver.com/webhooks/github
      Secret: (same as webhook_secret above)
    """
    result = models.upsert_integration(user["id"], "github", config.model_dump())
    return {
        "status": "connected",
        "next_step": "Add webhook in GitHub: repo → Settings → Webhooks",
        "webhook_url": "http://localhost:8000/webhooks/github",
        "integration": result,
    }


# ── List all integrations ────────────────────────────────────────────────────

@router.get("/")
async def list_integrations(user=Depends(get_current_user)):
    """Return all connected integrations for the current user."""
    integrations = models.get_integrations(user["id"])
    # Mask sensitive fields before returning.
    for i in integrations:
        if "bot_token" in i.get("config", {}):
            i["config"]["bot_token"] = "xoxb-***"
        if "webhook_secret" in i.get("config", {}):
            i["config"]["webhook_secret"] = "***"
    return {"integrations": integrations}


@router.delete("/{integration_type}")
async def disconnect(integration_type: str, user=Depends(get_current_user)):
    """Disable an integration without deleting its config."""
    conn = models.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE integrations SET enabled = FALSE "
                "WHERE user_id = %s AND type = %s",
                (user["id"], integration_type)
            )
        conn.commit()
    finally:
        models.put_conn(conn)
    return {"status": "disconnected", "type": integration_type}