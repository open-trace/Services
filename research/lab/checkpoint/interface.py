from __future__ import annotations

from typing import Protocol


class Checkpoint(Protocol):
    """Track source IDs already acquired (dedupe / resume)."""

    def is_seen(self, source_id: str) -> bool: ...

    def mark_seen(self, source_id: str) -> None: ...
