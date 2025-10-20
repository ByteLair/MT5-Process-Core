# api/middleware_auth.py
import os
import time
from collections.abc import Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

# Simple in-memory rate limiter: key => [window_start_epoch, count]
_RATE = {}
WINDOW = int(os.getenv("RATE_WINDOW_SECONDS", "60"))
LIMIT = int(os.getenv("RATE_LIMIT", "300"))  # requests per window
HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")
API_KEY = os.getenv("API_KEY", "")


def _key_from_request(req: Request) -> str:
    ip = req.client.host if req.client else "unknown"
    key = req.headers.get(HEADER, "")
    return f"{ip}:{key}"


class APIKeyAndRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # Auth
        provided = request.headers.get(HEADER, "")
        if not API_KEY or provided != API_KEY:
            raise HTTPException(status_code=401, detail="unauthorized")
        # Rate limit
        now = int(time.time())
        bucket = _key_from_request(request)
        start, count = _RATE.get(bucket, (now, 0))
        if now - start >= WINDOW:
            start, count = now, 0
        count += 1
        _RATE[bucket] = (start, count)
        if count > LIMIT:
            raise HTTPException(status_code=429, detail="rate limited")
        return await call_next(request)
