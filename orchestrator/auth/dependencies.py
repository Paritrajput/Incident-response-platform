"""
auth/dependencies.py

FastAPI authentication dependency.

Reads the JWT from the httpOnly cookie,
verifies it, loads the user from the database,
and returns the authenticated user.

Every protected endpoint should depend on:

    user: dict = Depends(get_current_user)

instead of API keys.
"""

from fastapi import Cookie, Depends, HTTPException, status

from auth.jwt_handler import verify_access_token
from db import models


def get_current_user(
    access_token: str | None = Cookie(default=None),
) -> dict:
    """
    Authenticate the current request.

    The browser automatically sends the httpOnly cookie.

    Returns
    -------
    dict
        Authenticated user.

    Raises
    ------
    HTTPException(401)
        Missing cookie
        Invalid token
        Expired token
        User no longer exists
    """

    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = verify_access_token(access_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user_id = int(payload["sub"])

    user = models.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user