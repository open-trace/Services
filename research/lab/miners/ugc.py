from __future__ import annotations

from lab.miners.youtube import _StubMiner


class UgcMiner(_StubMiner):
    def __init__(self) -> None:
        super().__init__(
            "ugc",
            "ugc",
            "Blogs and open comment sections — raw text dumps with source URL metadata",
        )
