from __future__ import annotations

import json

import httpx

from lab.checkpoint.interface import Checkpoint
from lab.miners.arxiv.client import (
    ARXIV_RATE_LIMIT_S,
    download_pdf,
    entry_to_meta,
    iter_entries,
)
from lab.models import MinerConfig, RunManifest, utc_now
from lab.store.interface import RawStore


class ArxivMiner:
    corpus = "arxiv"

    def acquire(
        self,
        config: MinerConfig,
        store: RawStore,
        checkpoint: Checkpoint,
    ) -> RunManifest:
        query = str(config.extras.get("query", "all:agriculture")).strip()
        if not query:
            raise ValueError("arxiv miner requires extras['query']")

        manifest = RunManifest(
            run_id="",
            corpus=self.corpus,
            miner_name="arxiv",
            started_at=utc_now(),
            storage_prefix=store.storage_prefix,
        )

        rate_limit = float(config.extras.get("rate_limit_s", ARXIV_RATE_LIMIT_S))

        with httpx.Client(headers={"User-Agent": "OpenTrace-Lab/0.1"}) as client:
            entries = iter_entries(
                client,
                query,
                max_results=config.max_results,
                rate_limit_s=rate_limit,
            )

            for entry in entries:
                source_id = entry.arxiv_id.replace("/", "_")
                if checkpoint.is_seen(source_id) or store.exists(self.corpus, source_id):
                    manifest.skipped += 1
                    continue

                try:
                    meta = entry_to_meta(entry)
                    if config.download_pdf:
                        pdf_bytes = download_pdf(client, entry.pdf_url)
                        store.put(
                            self.corpus,
                            source_id,
                            "artifact.pdf",
                            pdf_bytes,
                            {**meta, "mime": "application/pdf"},
                        )
                    else:
                        meta_bytes = json.dumps(meta, indent=2, ensure_ascii=False).encode("utf-8")
                        store.put(
                            self.corpus,
                            source_id,
                            "artifact.json",
                            meta_bytes,
                            {**meta, "mime": "application/json"},
                        )

                    checkpoint.mark_seen(source_id)
                    manifest.fetched += 1
                except Exception as exc:
                    manifest.failed += 1
                    manifest.errors.append(f"{source_id}: {exc}")

        manifest.finished_at = utc_now()
        return manifest
