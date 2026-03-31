"""Rate limiter utilities with optional Redis support."""
from collections import deque
from dataclasses import dataclass
from math import ceil
from typing import Deque, Dict
import asyncio
import logging
import time

from app.config import settings

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover - redis is optional
    redis = None

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result object returned after checking/consuming a rate limit."""

    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int
    retry_after: int | None = None


class InMemoryRateLimiter:
    """Per-key fixed-window limiter using in-memory buckets."""

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self._buckets: Dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    def reset(self) -> None:
        """Reset all counters (useful for tests)."""
        self._buckets.clear()

    async def consume(self, key: str, limit: int) -> RateLimitResult:
        """Consume one token for `key` if still under the current limit."""
        if limit <= 0:
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_seconds=self.window_seconds,
                retry_after=self.window_seconds,
            )

        now = time.time()

        async with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            self._prune(bucket, now)

            if len(bucket) >= limit:
                reset_seconds = max(
                    1,
                    ceil(self.window_seconds - (now - bucket[0])) if bucket else self.window_seconds,
                )
                return RateLimitResult(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_seconds=reset_seconds,
                    retry_after=reset_seconds,
                )

            bucket.append(now)
            remaining = max(limit - len(bucket), 0)
            reset_seconds = max(
                1,
                ceil(self.window_seconds - (now - bucket[0])) if bucket else self.window_seconds,
            )
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=remaining,
                reset_seconds=reset_seconds,
            )

    def _prune(self, bucket: Deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()


class RedisRateLimiter:
    """Redis-backed fixed-window limiter."""

    def __init__(self, redis_url: str, window_seconds: int = 60, key_prefix: str = "rate_limit"):
        if redis is None:
            raise RuntimeError("redis package is required for Redis rate limiting")

        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
        self._client = redis.from_url(redis_url, decode_responses=True)

    def _key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    def reset(self) -> None:
        """Best-effort reset of limiter keys."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._reset_async())
            else:
                loop.run_until_complete(self._reset_async())
        except RuntimeError:
            asyncio.run(self._reset_async())

    async def _reset_async(self) -> None:
        cursor = "0"
        pattern = f"{self.key_prefix}:*"
        while True:
            cursor, keys = await self._client.scan(cursor=cursor, match=pattern, count=200)
            if keys:
                await self._client.delete(*keys)
            if cursor == "0":
                break

    async def consume(self, key: str, limit: int) -> RateLimitResult:
        """Consume one token for `key` if still under the current limit."""
        if limit <= 0:
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_seconds=self.window_seconds,
                retry_after=self.window_seconds,
            )

        redis_key = self._key(key)

        try:
            async with self._client.pipeline() as pipe:
                pipe.incr(redis_key)
                pipe.ttl(redis_key)
                count, ttl = await pipe.execute()

            if ttl == -1:
                await self._client.expire(redis_key, self.window_seconds)
                ttl = self.window_seconds
            if ttl is None or ttl < 0:
                ttl = self.window_seconds

            allowed = count <= limit
            remaining = max(limit - count, 0)
            reset_seconds = max(1, int(ttl))

            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                reset_seconds=reset_seconds,
                retry_after=reset_seconds if not allowed else None,
            )
        except Exception:
            logger.exception("Redis rate limiter error")
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_seconds=self.window_seconds,
            )


def _build_rate_limiter():
    window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS
    if settings.RATE_LIMIT_STORE == "redis":
        return RedisRateLimiter(settings.REDIS_URL, window_seconds=window_seconds)
    return InMemoryRateLimiter(window_seconds=window_seconds)


rate_limiter = _build_rate_limiter()