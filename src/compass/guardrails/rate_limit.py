"""Thread-safe sliding-window rate limiter, keyed by caller identity.

Unlike the gateway's ``RateLimiter`` (which is bypassed on the unauthenticated
demo path), this one is invoked inside the guardrail pipeline so *every* query
flow is covered, authenticated or not.
"""

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """Per-identity request cap over 60s and 3600s windows."""

    def __init__(self, per_minute: int, per_hour: int):
        self.per_minute = per_minute
        self.per_hour = per_hour
        self._events: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, identity: str, now: float | None = None) -> bool:
        """Record a request for ``identity`` and report whether it is allowed."""
        now = time.time() if now is None else now
        minute_ago = now - 60
        hour_ago = now - 3600
        with self._lock:
            dq = self._events[identity]
            while dq and dq[0] <= hour_ago:
                dq.popleft()
            in_minute = sum(1 for ts in dq if ts > minute_ago)
            if in_minute >= self.per_minute or len(dq) >= self.per_hour:
                return False
            dq.append(now)
            return True

    def reset(self, identity: str | None = None) -> None:
        with self._lock:
            if identity is None:
                self._events.clear()
            else:
                self._events.pop(identity, None)
