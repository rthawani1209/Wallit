"""Small in-memory sliding-window rate limiter.

The API runs as a single process, so a dict of timestamps is enough; limits
reset on deploy. Moving to several workers would mean moving this to Redis,
which docker-compose already runs."""
import threading
import time
from collections import deque

# How often allow() sweeps out keys with no recent hits, so a script cycling
# through random emails can't grow the table forever.
SWEEP_EVERY = 1000


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()
        self._calls = 0

    def allow(self, key: str) -> bool:
        """Record a hit for `key` and say whether it's within the limit."""
        now = time.monotonic()
        with self._lock:
            self._calls += 1
            if self._calls % SWEEP_EVERY == 0:
                self._sweep(now)
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True

    def _sweep(self, now: float) -> None:
        stale = [k for k, hits in self._hits.items() if not hits or now - hits[-1] > self.window]
        for k in stale:
            del self._hits[k]

    def __len__(self) -> int:
        return len(self._hits)

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
