"""
auth/security.py

Cookie helper utilities.

Centralizes cookie configuration so every
login/logout uses identical settings.
"""

from fastapi import Response


COOKIE_NAME = "access_token"


def set_auth_cookie(
    response: Response,
    token: str,
) -> None:
    """
    Store JWT inside an httpOnly cookie.
    """

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,

        httponly=True,

        secure=False,      # True in production (HTTPS)

        samesite="lax",

        max_age=60 * 60 * 24 * 7,

        path="/",
    )


def clear_auth_cookie(
    response: Response,
) -> None:
    """
    Remove authentication cookie.
    """

    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
    )