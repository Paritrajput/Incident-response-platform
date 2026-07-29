"""
integrations/github.py

GitHub webhook receiver.

Responsibilities
----------------
1. Receive GitHub webhook events.
2. Verify webhook signature.
3. Identify which application owns the webhook.
4. Convert GitHub Push events into Deploy events.
5. Persist deploys.
6. Feed the deploy correlator.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

from agents import deploy_correlator
from db import models

router = APIRouter()

# -------------------------------------------------------------------
# In-memory deploy cache (survives only until restart)
# -------------------------------------------------------------------

recent_github_deploys = []


# -------------------------------------------------------------------
# Signature Verification
# -------------------------------------------------------------------

def verify_signature(
    payload_bytes: bytes,
    signature: str,
    secret: str,
) -> bool:

    if not signature:
        return False

    if not signature.startswith("sha256="):
        return False

    expected = (
        "sha256="
        + hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected, signature)


# -------------------------------------------------------------------
# Find which application sent this webhook
# -------------------------------------------------------------------

def identify_application(
    payload_bytes: bytes,
    signature: str,
):
    """
    Iterate over every GitHub integration until
    a webhook secret matches.
    """

    applications = models.get_all_applications_with_integration(
        "github"
    )

    for app in applications:

        config = app.get("config", {})
        secret = config.get("webhook_secret")

        if not secret:
            continue

        if verify_signature(
            payload_bytes,
            signature,
            secret,
        ):
            return app

    return None


# -------------------------------------------------------------------
# Webhook
# -------------------------------------------------------------------

@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):

    payload_bytes = await request.body()

    print(
        f"[GITHUB] webhook received "
        f"event={x_github_event}",
        flush=True,
    )

    # -------------------------------------------------------------
    # Identify application
    # -------------------------------------------------------------

    application = identify_application(
        payload_bytes,
        x_hub_signature_256,
    )

    if application is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )

    application_id = application["application_id"]

    try:
        payload = json.loads(payload_bytes)

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    # -------------------------------------------------------------
    # Ping Event
    # -------------------------------------------------------------

    if x_github_event == "ping":

        print(
            f"[GITHUB] Ping received "
            f"(application={application_id})",
            flush=True,
        )

        return {
            "status": "connected",
            "application_id": application_id,
        }

    # -------------------------------------------------------------
    # Ignore unsupported events
    # -------------------------------------------------------------

    if x_github_event != "push":

        return {
            "status": "ignored",
            "event": x_github_event,
        }

    # -------------------------------------------------------------
    # Push Event
    # -------------------------------------------------------------

    commits = payload.get("commits", [])

    if not commits:

        return {
            "status": "no_commits",
        }

    repository = payload.get(
        "repository",
        {},
    ).get(
        "full_name",
        "unknown",
    )

    ref = payload.get(
        "ref",
        "",
    )

    config = application.get("config", {})

    service_name = (
        config.get("repo_to_service", {})
        .get(
            repository,
            repository.split("/")[-1],
        )
    )

    latest_commit = commits[-1]

    deploy = {
        "application_id": application_id,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "service": service_name,
        "deploy_id": latest_commit.get(
            "id",
            "",
        )[:8],
        "commit_message": latest_commit.get(
            "message",
            "",
        ),
        "branch": ref.replace(
            "refs/heads/",
            "",
        ),
        "source": "github",
    }

    # -------------------------------------------------------------
    # Cache
    # -------------------------------------------------------------

    recent_github_deploys.append(deploy)

    # -------------------------------------------------------------
    # Persist
    # -------------------------------------------------------------

    try:

        models.save_deploy(deploy)

    except Exception as e:

        print(
            f"[GITHUB] failed to save deploy: {e}",
            flush=True,
        )

    # -------------------------------------------------------------
    # Correlator
    # -------------------------------------------------------------

    try:

        deploy_correlator.record_deploy(deploy)

    except Exception as e:

        print(
            f"[GITHUB] correlator error: {e}",
            flush=True,
        )

    print(
        "[GITHUB] Deploy recorded "
        f"(application={application_id}, "
        f"service={service_name})",
        flush=True,
    )

    return {
        "status": "received",
        "application_id": application_id,
        "service": service_name,
    }