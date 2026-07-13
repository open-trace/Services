from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredRef:
    corpus: str
    source_id: str
    uri: str
    bytes_written: int


class RawStore(Protocol):
    """Store raw artifacts. Callers pass corpus, source_id, filename, bytes, and meta dict."""

    def put(
        self,
        corpus: str,
        source_id: str,
        filename: str,
        content: bytes,
        meta: dict,
    ) -> StoredRef: ...

    def exists(self, corpus: str, source_id: str) -> bool: ...

    @property
    def storage_prefix(self) -> str: ...
