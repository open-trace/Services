from __future__ import annotations

from lab.miners.youtube import _StubMiner


class NewsMiner(_StubMiner):
    def __init__(self) -> None:
        super().__init__(
            "news",
            "news",
            "News/RSS harvest — raw HTML/PDF only; independent from ml-eng web_data_mining",
        )
