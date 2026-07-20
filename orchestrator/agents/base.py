"""
base.py - Shared Gemini call helper used by all agents.

Centralizes rate-limit handling so each agent doesn't duplicate it.
Gemini returns 429 ResourceExhausted when you exceed quota. We catch
it specifically and wait longer than the normal retry backoff.
"""

import asyncio
from google.api_core.exceptions import ResourceExhausted


async def call_gemini_with_backoff(call_fn, max_attempts: int = 3) -> str:
    """
    Run a synchronous Gemini call in a thread, with specific handling
    for rate limit errors (429 ResourceExhausted).

    Normal errors: retry with 2s, 4s backoff.
    Rate limit errors: retry with 15s, 30s backoff (quota resets slowly).
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await asyncio.to_thread(call_fn)

        except ResourceExhausted as e:
            if attempt == max_attempts:
                raise
            wait = 15 * attempt  # 15s, 30s — quota windows are long
            print(f"[rate limit] attempt {attempt}, waiting {wait}s: {e}")
            await asyncio.sleep(wait)

        except Exception:
            if attempt == max_attempts:
                raise
            await asyncio.sleep(2 ** attempt)

    raise RuntimeError("call_gemini_with_backoff: exhausted retries")