"""In-memory token bucket rate limiter per client IP address."""

import math
import time
from threading import Lock
from typing import Dict, Tuple


class RateLimiter:
    """Token bucket rate limiter tracking requests per client IP."""

    def __init__(self, rate_per_min: int = 20):
        self.rate_per_min = max(1, rate_per_min)
        self.capacity = float(self.rate_per_min)
        self.fill_rate = float(self.rate_per_min) / 60.0  # tokens per second
        self.buckets: Dict[str, Tuple[float, float]] = {}  # ip -> (tokens, last_updated)
        self.lock = Lock()

    def set_rate(self, rate_per_min: int) -> None:
        """Update rate limit dynamically (useful for tests)."""
        with self.lock:
            self.rate_per_min = max(1, rate_per_min)
            self.capacity = float(self.rate_per_min)
            self.fill_rate = float(self.rate_per_min) / 60.0

    def check(self, client_ip: str) -> Tuple[bool, int]:
        """
        Check if client_ip is allowed to make a request.
        Returns: (is_allowed, retry_after_seconds)
        """
        now = time.monotonic()

        with self.lock:
            if client_ip not in self.buckets:
                # First request from this IP: allow and consume 1 token
                self.buckets[client_ip] = (self.capacity - 1.0, now)
                return True, 0

            tokens, last_updated = self.buckets[client_ip]
            elapsed = max(0.0, now - last_updated)
            tokens = min(self.capacity, tokens + elapsed * self.fill_rate)

            if tokens >= 1.0:
                self.buckets[client_ip] = (tokens - 1.0, now)
                return True, 0
            else:
                needed = 1.0 - tokens
                retry_after = max(1, math.ceil(needed / self.fill_rate))
                self.buckets[client_ip] = (tokens, now)
                return False, retry_after

    def reset(self) -> None:
        """Clear all rate limiting state."""
        with self.lock:
            self.buckets.clear()
