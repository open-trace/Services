from __future__ import annotations


class InMemoryCheckpoint:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def is_seen(self, source_id: str) -> bool:
        return source_id in self._seen

    def mark_seen(self, source_id: str) -> None:
        self._seen.add(source_id)
