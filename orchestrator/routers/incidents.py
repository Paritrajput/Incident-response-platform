"""
routers/incidents.py - Incident history REST API.

Lets users query their incident history. The dashboard calls this
on load to show past incidents before the WebSocket catches up.
"""

from fastapi import APIRouter, Depends, Query
from routers.auth import get_current_user
from db import models

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("/")
async def list_incidents(
    limit: int = Query(default=20, le=100),
    user=Depends(get_current_user)
):
    """Return recent incidents for the authenticated user."""
    incidents = models.get_incidents(user["id"], limit=limit)
    return {"incidents": incidents, "count": len(incidents)}