"""
UgcMiner — Blog and user-generated content harvest for African agriculture.

Reuses the same RSS + trafilatura approach as NewsMiner but targets
agricultural blogs, extension service sites, and community platforms.

Usage:
    python -m lab.cli acquire ugc --max-results 50
    python -m lab.cli acquire ugc --extras '{"countries":["Kenya"],"dry_run":true}'
"""
from __future__ import annotations

from pathlib import Path

from lab.checkpoint.interface import Checkpoint
from lab.miners.news import (
    NewsMiner,
    _DEFAULT_FEEDS_PATH,
)
from lab.models import MinerConfig, RunManifest
from lab.store.interface import RawStore

# UGC uses a separate feeds file (blogs, extension services, substack, etc.)
_DEFAULT_UGC_FEEDS_PATH = Path(__file__).resolve().parent / "feeds" / "ugc_feeds.json"


class UgcMiner:
    corpus = "ugc"

    def acquire(
        self,
        config: MinerConfig,
        store: RawStore,
        checkpoint: Checkpoint,
    ) -> RunManifest:
        """Acquire blog/UGC content. Delegates to NewsMiner logic with UGC feeds."""
        # Override feeds path to UGC-specific feeds, unless caller specified one
        extras = dict(config.extras)
        if "feeds_path" not in extras:
            extras["feeds_path"] = str(_DEFAULT_UGC_FEEDS_PATH)

        ugc_config = MinerConfig(
            max_results=config.max_results,
            download_pdf=config.download_pdf,
            extras=extras,
        )

        # Reuse NewsMiner logic but with UGC corpus name
        _inner = _UgcInnerMiner()
        return _inner.acquire(ugc_config, store, checkpoint)


class _UgcInnerMiner(NewsMiner):
    """NewsMiner subclass with corpus='ugc' and doc_kind='blog_article'."""

    corpus = "ugc"

    def _doc_kind(self) -> str:
        return "blog_article"
