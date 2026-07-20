import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request, Header

router = APIRouter()


def verify_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_bytes, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# Store deploys in memory directly here - no import needed
recent_github_deploys = []


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
):
    payload_bytes = await request.body()

    # Write directly to stdout - bypasses logger module entirely
    print(f"[GITHUB] webhook received event={x_github_event} size={len(payload_bytes)}", flush=True)

    try:
        payload = json.loads(payload_bytes)
    except Exception as e:
        print(f"[GITHUB] failed to parse payload: {e}", flush=True)
        return {"status": "parse_error"}

    if x_github_event == "push":
        commits = payload.get("commits", [])
        repo = payload.get("repository", {}).get("full_name", "unknown")
        ref = payload.get("ref", "")

        print(f"[GITHUB] push event repo={repo} ref={ref} commits={len(commits)}", flush=True)

        if commits:
            latest = commits[-1]
            deploy = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": repo.split("/")[-1],
                "deploy_id": latest.get("id", "")[:8],
                "commit_message": latest.get("message", ""),
                "branch": ref.replace("refs/heads/", ""),
                "source": "github",
            }
            recent_github_deploys.append(deploy)
            print(f"[GITHUB] deploy recorded: {deploy}", flush=True)

            # Feed into deploy correlator cache
            try:
                from agents import deploy_correlator
                deploy_correlator.record_deploy(deploy)
                print(f"[GITHUB] deploy added to correlator cache", flush=True)
            except Exception as e:
                print(f"[GITHUB] correlator import failed: {e}", flush=True)

    elif x_github_event == "ping":
        print(f"[GITHUB] ping received - webhook connected successfully!", flush=True)

    return {"status": "received"}