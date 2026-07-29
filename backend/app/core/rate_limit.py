from collections import deque
from dataclasses import dataclass
from hashlib import sha256
from math import ceil
from threading import Lock
from time import monotonic
from typing import Callable


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int = 0


class InMemoryRateLimiter:
    def __init__(
        self,
        *,
        max_entries: int,
        clock: Callable[[], float] = monotonic,
    ):
        self.max_entries = max_entries
        self.clock = clock
        self._attempts: dict[str, deque[float]] = {}
        self._lock = Lock()

    @property
    def entry_count(self) -> int:
        with self._lock:
            return len(self._attempts)

    def consume(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        now = self.clock()
        cutoff = now - window_seconds

        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is not None:
                while attempts and attempts[0] <= cutoff:
                    attempts.popleft()
                if not attempts:
                    self._attempts.pop(key, None)
                    attempts = None

            if attempts is None:
                self._make_room(cutoff)
                attempts = deque()
                self._attempts[key] = attempts

            if len(attempts) >= limit:
                retry_after = max(
                    1,
                    ceil(window_seconds - (now - attempts[0])),
                )
                return RateLimitResult(False, retry_after)

            attempts.append(now)
            return RateLimitResult(True)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()

    def _make_room(self, cutoff: float) -> None:
        expired = [
            key
            for key, attempts in self._attempts.items()
            if not attempts or attempts[-1] <= cutoff
        ]
        for key in expired:
            self._attempts.pop(key, None)

        if len(self._attempts) < self.max_entries:
            return

        oldest_key = min(
            self._attempts,
            key=lambda key: self._attempts[key][-1],
        )
        self._attempts.pop(oldest_key, None)


def rate_limit_key(namespace: str, client_host: str, identity: str) -> str:
    value = f"{namespace}\0{client_host}\0{identity}".encode("utf-8")
    return sha256(value).hexdigest()
