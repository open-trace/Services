from __future__ import annotations

from lab.miners.youtube import _StubMiner


class ManualsMiner(_StubMiner):
    def __init__(self) -> None:
        super().__init__(
            "manuals",
            "manuals",
            "Agricultural practice manuals and open textbooks (PDF/HTML download)",
        )
