from __future__ import annotations

from lab.models import MinerConfig, RunManifest, utc_now
from lab.checkpoint.interface import Checkpoint
from lab.store.interface import RawStore


class _StubMiner:
    corpus: str
    _name: str
    _poc_note: str

    def __init__(self, corpus: str, name: str, poc_note: str) -> None:
        self.corpus = corpus
        self._name = name
        self._poc_note = poc_note

    def acquire(
        self,
        config: MinerConfig,
        store: RawStore,
        checkpoint: Checkpoint,
    ) -> RunManifest:
        raise NotImplementedError(
            f"{self._name} miner is not implemented yet. POC scope: {self._poc_note}"
        )


class YoutubeMiner(_StubMiner):
    def __init__(self) -> None:
        super().__init__(
            "youtube",
            "youtube",
            "Agripreneur how-to video transcripts via YouTube Data API or transcript APIs",
        )
