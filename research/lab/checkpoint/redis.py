from __future__ import annotations


class RedisCheckpoint:
    """Redis-backed seen-ID set for long mining runs."""

    def __init__(self, url: str, corpus: str) -> None:
        import redis

        self._corpus = corpus.replace(":", "_")
        self._client = redis.Redis.from_url(url, decode_responses=True)
        self._client.ping()

    def _key(self, source_id: str) -> str:
        return f"lab:checkpoint:{self._corpus}:{source_id}"

    def is_seen(self, source_id: str) -> bool:
        return bool(self._client.exists(self._key(source_id)))

    def mark_seen(self, source_id: str) -> None:
        self._client.set(self._key(source_id), "1")
