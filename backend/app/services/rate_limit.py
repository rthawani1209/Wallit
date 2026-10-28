"""Small in-memory sliding-window rate limiter.

The API runs as a single process, so a dict of timestamps is enough; limits
reset on deploy. Moving to several workers would mean moving this to Redis,
which docker-compose already runs."""
import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Record a hit for `key` and say whether it's within the limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# One limiter per thing worth protecting. Numbers are generous for a person and
# tight for a script.
login_limiter = SlidingWindowLimiter(limit=10, window_seconds=15 * 60)  # per IP + email
signup_limiter = SlidingWindowLimiter(limit=5, window_seconds=60 * 60)  # per IP
chat_limiter = SlidingWindowLimiter(limit=40, window_seconds=60 * 60)  # per user; each message is a paid call
demo_limiter = SlidingWindowLimiter(limit=10, window_seconds=60 * 60)  # new demo sessions per IP


def reset_all() -> None:
    for limiter in (login_limiter, signup_limiter, chat_limiter, demo_limiter):
        limiter.reset()
