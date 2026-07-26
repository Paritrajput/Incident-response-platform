"""
auth/jwt_handler.py

JWT creation and verification.

This module is responsible only for:
- Creating JWT access tokens
- Verifying JWTs
- Returning the decoded payload

No FastAPI code belongs here.
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from config import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_DAYS,
)


def create_access_token(user: dict) -> str:
    """
    Create a signed JWT for a user.

    Payload contains only the minimum required information.
    """

    expire = datetime.now(timezone.utc) + timedelta(
        days=ACCESS_TOKEN_EXPIRE_DAYS
    )

    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "email": user["email"],
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return token


def verify_access_token(token: str) -> dict | None:
    """
    Verify a JWT.

    Returns:
        dict    -> decoded payload
        None    -> invalid / expired token
    """

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        return payload

    except JWTError:
        return None