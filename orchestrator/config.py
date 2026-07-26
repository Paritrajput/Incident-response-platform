"""
config.py - All environment variables loaded in one place.

Every other module imports from here. This means:
- If a variable is missing, we fail fast on startup with a clear error.
- Nothing else calls dotenv directly, keeping things clean.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    """Get an env variable, crash with a helpful message if it's missing."""
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


GEMINI_API_KEY = _require("GEMINI_API_KEY")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "30"))
AGENT_MAX_RETRIES = int(os.getenv("AGENT_MAX_RETRIES", "2"))
JWT_SECRET_KEY = _require("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7")
)
FRONTEND_URLS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]