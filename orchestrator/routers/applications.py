from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth.dependencies import get_current_user
from db import models

router = APIRouter(
    prefix="/applications",
    tags=["applications"],
)


class CreateApplicationRequest(BaseModel):
    name: str
    description: str = ""


class UpdateApplicationRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    is_default: bool | None = None


def _owned_application(application_id: int, user_id: int) -> dict:
    if not models.application_belongs_to_user(application_id, user_id):
        raise HTTPException(status_code=404, detail="Application not found")
    return models.get_application(application_id)


@router.post("/")
async def create_application(
    body: CreateApplicationRequest,
    user=Depends(get_current_user),
):

    app = models.create_application(
        user["id"],
        body.name,
        body.description,
    )

    return app


@router.get("/")
async def list_applications(
    user=Depends(get_current_user),
):

    return models.get_applications(user["id"])


@router.get("/{application_id}")
async def get_application(application_id: int, user=Depends(get_current_user)):
    return _owned_application(application_id, user["id"])


@router.put("/{application_id}")
async def update_application(
    application_id: int,
    body: UpdateApplicationRequest,
    user=Depends(get_current_user),
):
    _owned_application(application_id, user["id"])
    updated = models.update_application(
        application_id,
        user["id"],
        body.model_dump(exclude_none=True),
    )
    return updated


@router.delete("/{application_id}")
async def delete_application(application_id: int, user=Depends(get_current_user)):
    if not models.delete_application(application_id, user["id"]):
        raise HTTPException(status_code=404, detail="Application not found")
    return {"status": "deleted"}


@router.get("/{application_id}/incidents")
async def list_application_incidents(
    application_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    user=Depends(get_current_user),
):
    _owned_application(application_id, user["id"])
    incidents = models.get_incidents(application_id, limit=limit)
    return {"incidents": incidents, "count": len(incidents)}


@router.get("/{application_id}/deploys")
async def list_application_deploys(
    application_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    user=Depends(get_current_user),
):
    _owned_application(application_id, user["id"])
    deploys = models.get_deploys(application_id, limit=limit)
    return {"deploys": deploys, "count": len(deploys)}
