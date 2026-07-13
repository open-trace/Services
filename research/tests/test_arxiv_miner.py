from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from lab.checkpoint.memory import InMemoryCheckpoint
from lab.miners.arxiv.client import ArxivEntry
from lab.miners.arxiv.miner import ArxivMiner
from lab.models import MinerConfig
from lab.store.local import LocalFilesystemStore


def _sample_entry() -> ArxivEntry:
    return ArxivEntry(
        arxiv_id="2301.00001v1",
        title="Test Agriculture Paper",
        abstract="Abstract about crops.",
        authors=["Jane Doe"],
        categories=["cs.AI"],
        published="2023-01-01T00:00:00Z",
        pdf_url="https://arxiv.org/pdf/2301.00001v1.pdf",
        abs_url="https://arxiv.org/abs/2301.00001v1",
    )


def test_arxiv_miner_stores_pdf_and_meta(tmp_path: Path) -> None:
    store = LocalFilesystemStore(tmp_path)
    checkpoint = InMemoryCheckpoint()
    miner = ArxivMiner()
    config = MinerConfig(
        max_results=1,
        download_pdf=True,
        extras={"query": "all:agriculture", "rate_limit_s": 0},
    )

    with patch("lab.miners.arxiv.miner.iter_entries", return_value=[_sample_entry()]):
        with patch("lab.miners.arxiv.miner.download_pdf", return_value=b"%PDF-fake"):
            result = miner.acquire(config, store, checkpoint)

    assert result.fetched == 1
    assert result.failed == 0
    assert store.exists("arxiv", "2301.00001v1")

    artifact_dir = tmp_path / "arxiv" / "2301.00001v1"
    assert (artifact_dir / "artifact.pdf").read_bytes() == b"%PDF-fake"
    meta = json.loads((artifact_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["arxiv_id"] == "2301.00001v1"
    assert "Agriculture" in meta["title"]


def test_arxiv_miner_skips_seen(tmp_path: Path) -> None:
    store = LocalFilesystemStore(tmp_path)
    checkpoint = InMemoryCheckpoint()
    checkpoint.mark_seen("2301.00001v1")
    miner = ArxivMiner()
    config = MinerConfig(
        max_results=1,
        download_pdf=False,
        extras={"query": "all:agriculture", "rate_limit_s": 0},
    )

    with patch("lab.miners.arxiv.miner.iter_entries", return_value=[_sample_entry()]):
        result = miner.acquire(config, store, checkpoint)

    assert result.fetched == 0
    assert result.skipped == 1
