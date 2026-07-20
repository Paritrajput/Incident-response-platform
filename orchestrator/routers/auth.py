"""
routers/auth.py - API key authentication + user signup.

Simple but real:
  POST /auth/signup   → creates a user, returns their API key
  GET  /auth/me       → returns user info for a given API key

Every protected endpoint calls get_current_user() as a FastAPI
dependency. If the API key is missing or wrong, it returns 401.

In a real product you'd add email verification and eventually
replace API keys with OAuth. But API keys are fine for v1 — they're
what Stripe, GitHub, and most developer tools used at launch.
"""

from fastapi import APIRouter, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from db import models

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer()


class SignupRequest(BaseModel):
    email: str   # using str instead of EmailStr to avoid email-validator dep


class SignupResponse(BaseModel):
    email: str
    api_key: str
    message: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer)
) -> dict:
    """
    FastAPI dependency. Use as:
        user = Depends(get_current_user)

    Reads the Bearer token from the Authorization header and
    looks up the user in Postgres. Returns the user dict or raises 401.
    """
    user = models.get_user_by_api_key(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user


@router.post("/signup", response_model=SignupResponse)
async def signup(body: SignupRequest):
    """
    Create a new user account. Returns an API key immediately.
    No email verification for v1 — add it when you have real users.
    """
    existing = models.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.create_user(body.email)
    return SignupResponse(
        email=user["email"],
        api_key=user["api_key"],
        message="Save your API key — it won't be shown again."
    )


@router.get("/me")
async def me(credentials: HTTPAuthorizationCredentials = Security(bearer)):
    """Return the current user's info."""
    user = get_current_user(credentials)
    return {"email": user["email"], "user_id": user["id"]}