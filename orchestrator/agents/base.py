import time

import asyncio
from google.api_core.exceptions import ResourceExhausted

# Max concurrent Gemini API calls across all agents.
# Free tier: 5 req/min. 2 concurrent + retries keeps us under.
_gemini_semaphore = asyncio.Semaphore(2)

# Circuit breaker state
_failure_count = 0
_last_failure_time = 0.0
_circuit_open = False
FAILURE_THRESHOLD = 5      # open circuit after 5 consecutive failures
RECOVERY_TIMEOUT = 60      # try again after 60 seconds


def _record_success():
    global _failure_count, _circuit_open
    _failure_count = 0
    _circuit_open = False


def _record_failure():
    global _failure_count, _last_failure_time, _circuit_open
    _failure_count += 1
    _last_failure_time = time.time()
    if _failure_count >= FAILURE_THRESHOLD:
        _circuit_open = True
        print(f"[GEMINI] circuit breaker OPEN after {_failure_count} failures", flush=True)


def _is_circuit_open() -> bool:
    global _circuit_open, _failure_count
    if not _circuit_open:
        return False
    # Try recovery after timeout
    if time.time() - _last_failure_time > RECOVERY_TIMEOUT:
        _circuit_open = False
        _failure_count = 0
        print("[GEMINI] circuit breaker attempting RECOVERY", flush=True)
        return False
    return True


async def call_gemini_with_backoff(call_fn, max_attempts: int = 3) -> str:
    """
    Run a synchronous Gemini call in a thread with:
    - Circuit breaker (stops calls if Gemini is consistently failing)
    - Semaphore (limits to 2 concurrent calls)
    - Rate limit handling with longer backoff
    - General exception retry with exponential backoff
    """
    if _is_circuit_open():
        raise RuntimeError("Gemini circuit breaker is open - too many recent failures")

    async with _gemini_semaphore:
        for attempt in range(1, max_attempts + 1):
            try:
                result = await asyncio.to_thread(call_fn)
                _record_success()
                return result

            except ResourceExhausted as e:
                _record_failure()
                if attempt == max_attempts:
                    raise
                wait = 15 * attempt
                print(f"[GEMINI] rate limited, waiting {wait}s (attempt {attempt})", flush=True)
                await asyncio.sleep(wait)

            except Exception as e:
                _record_failure()
                if attempt == max_attempts:
                    raise
                await asyncio.sleep(2 ** attempt)

    raise RuntimeError("call_gemini_with_backoff: exhausted retries")