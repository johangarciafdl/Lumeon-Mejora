from __future__ import annotations

import hashlib
import hmac
import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    def __init__(self, limit: int = 60, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            cutoff = now - self.window_seconds
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


def csrf_token(secret_key: str, session_id: str) -> str:
    return hmac.new(secret_key.encode(), session_id.encode(), hashlib.sha256).hexdigest()


def valid_csrf(secret_key: str, session_id: str, token: str | None) -> bool:
    if not token:
        return False
    expected = csrf_token(secret_key, session_id)
    return hmac.compare_digest(expected, token)


assistant_limiter = RateLimiter(limit=30, window_seconds=60)
api_limiter = RateLimiter(limit=120, window_seconds=60)
