from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from threading import Lock


class SlidingWindowRateLimiter:
    """Простой in-memory sliding-window rate limiter для одного процесса."""

    def __init__(self, *, max_requests: int, window_seconds: int) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")

        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._checks = 0

    def check(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            bucket = self._requests[key]

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.max_requests:
                retry_after = max(
                    1,
                    math.ceil(self.window_seconds - (now - bucket[0])),
                )
                return False, retry_after

            bucket.append(now)
            self._checks += 1

            if self._checks % 100 == 0:
                self._cleanup_locked(cutoff)

            return True, 0

    def rollback_last(self, key: str) -> None:
        with self._lock:
            bucket = self._requests.get(key)

            if not bucket:
                return

            bucket.pop()

            if not bucket:
                self._requests.pop(key, None)

    def _cleanup_locked(self, cutoff: float) -> None:
        stale_keys: list[str] = []

        for key, bucket in self._requests.items():
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if not bucket:
                stale_keys.append(key)

        for key in stale_keys:
            self._requests.pop(key, None)


class OrderRateLimiter:
    """Ограничения на заявки:
    - не более 3 за 10 минут;
    - не более 6 за скользящие 24 часа.
    """

    def __init__(self) -> None:
        self.short_limit = SlidingWindowRateLimiter(
            max_requests=3,
            window_seconds=10 * 60,
        )
        self.daily_limit = SlidingWindowRateLimiter(
            max_requests=6,
            window_seconds=24 * 60 * 60,
        )

    def check(self, key: str) -> tuple[bool, int]:
        short_allowed, short_retry = self.short_limit.check(key)

        if not short_allowed:
            return False, short_retry

        daily_allowed, daily_retry = self.daily_limit.check(key)

        if not daily_allowed:
            self.short_limit.rollback_last(key)
            return False, daily_retry

        return True, 0


class FailedLoginRateLimiter:
    """Защита админки от перебора пароля.

    После 5 неудачных попыток с одного IP за 15 минут
    блокирует новые попытки с этого IP на 15 минут.
    """

    def __init__(
        self,
        *,
        max_failures: int = 1,
        failure_window_seconds: int = 15 * 60,
        block_seconds: int = 1 * 60,
    ) -> None:
        self.max_failures = max_failures
        self.failure_window_seconds = failure_window_seconds
        self.block_seconds = block_seconds

        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._blocked_until: dict[str, float] = {}
        self._lock = Lock()

    def is_blocked(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()

        with self._lock:
            blocked_until = self._blocked_until.get(key)

            if blocked_until is None:
                return False, 0

            if blocked_until <= now:
                self._blocked_until.pop(key, None)
                self._failures.pop(key, None)
                return False, 0

            return True, max(1, math.ceil(blocked_until - now))

    def record_failure(self, key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.failure_window_seconds

        with self._lock:
            blocked_until = self._blocked_until.get(key)

            if blocked_until is not None and blocked_until > now:
                return True, max(1, math.ceil(blocked_until - now))

            bucket = self._failures[key]

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            bucket.append(now)

            if len(bucket) >= self.max_failures:
                blocked_until = now + self.block_seconds
                self._blocked_until[key] = blocked_until
                bucket.clear()
                return True, self.block_seconds

            return False, 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._blocked_until.pop(key, None)


order_rate_limiter = OrderRateLimiter()
admin_login_rate_limiter = FailedLoginRateLimiter()
