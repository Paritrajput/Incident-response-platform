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
from fastapi import HTTPException

router = APIRouter(
    prefix=""
)


# ── Slack ────────────────────────────────────────────────────────────────────

class SlackConfig(BaseModel):
    bot_token: str       # xoxb-... from Slack app settings
    channel_id: str      # C... from Slack channel details


@router.post("/applications/{application_id}/integrations/slack")
async def connect_slack(application_id: int, config: SlackConfig, user=Depends(get_current_user)):
    
    """Save Slack credentials for the specified application."""
    if not models.application_belongs_to_user(
        application_id,
        user["id"],
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )
    result = models.upsert_integration(application_id, "slack", config.model_dump())
    return {"status": "connected", "integration": result}


# ── Prometheus ───────────────────────────────────────────────────────────────

class PrometheusConfig(BaseModel):
    prometheus_url: str             
    error_rate_query: Optional[str] = None   # custom PromQL or use default
    latency_query: Optional[str] = None


@router.post("/applications/{application_id}/integrations/prometheus")
async def connect_prometheus(application_id: int, config: PrometheusConfig, user=Depends(get_current_user)):
    """Save Prometheus config. The poller picks it up on next cycle."""
    if not models.application_belongs_to_user(
        application_id,
        user["id"],
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )
    result = models.upsert_integration(application_id, "prometheus", config.model_dump())
    return {"status": "connected", "integration": result}


# ── GitHub ───────────────────────────────────────────────────────────────────

class GitHubConfig(BaseModel):
    webhook_secret: str     # secret you set in GitHub webhook settings
    repo_to_service: Optional[dict] = {}    # {"my-org/my-repo": "payment-service"}


@router.post("/applications/{application_id}/integrations/github")
async def connect_github(application_id: int, config: GitHubConfig, user=Depends(get_current_user)):
    """
    Save GitHub webhook config.
    After calling this, set up the webhook in your GitHub repo:
      Settings → Webhooks → Add webhook
      URL: http://yourserver.com/webhooks/github
      Secret: (same as webhook_secret above)
    """
    if not models.application_belongs_to_user(
        application_id,
        user["id"],
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )
    result = models.upsert_integration(application_id, "github", config.model_dump())
    return {
        "status": "connected",
        "next_step": "Add webhook in GitHub: repo → Settings → Webhooks",
        "webhook_url": "http://localhost:8000/webhooks/github",
        "integration": result,
    }


# ── List all integrations ────────────────────────────────────────────────────

@router.get("/applications/{application_id}/integrations")
async def list_integrations(application_id: int, user=Depends(get_current_user)):
    """Return all connected integrations for the current user."""
    if not models.application_belongs_to_user(
        application_id,
        user["id"],
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )
    integrations = models.get_integrations(application_id)
    # Mask sensitive fields before returning.
    for i in integrations:
        if "bot_token" in i.get("config", {}):
            i["config"]["bot_token"] = "xoxb-***"
        if "webhook_secret" in i.get("config", {}):
            i["config"]["webhook_secret"] = "***"
    return {"integrations": integrations}


@router.delete("/applications/{application_id}/integrations/{integration_type}")
async def disconnect(application_id: int, integration_type: str, user=Depends(get_current_user)):
    """Disable an integration without deleting its config."""
    if not models.application_belongs_to_user(
        application_id,
        user["id"],
    ):
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )
    conn = models.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE integrations SET enabled = FALSE "
                "WHERE application_id = %s AND type = %s",
                (application_id, integration_type)
            )
        conn.commit()
    finally:
        models.put_conn(conn)
    return {"status": "disconnected", "type": integration_type}