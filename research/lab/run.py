from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Protocol

from lab.checkpoint.file import FileCheckpoint
from lab.checkpoint.interface import Checkpoint
from lab.checkpoint.memory import InMemoryCheckpoint
from lab.models import MinerConfig, RunManifest, utc_now
from lab.store.interface import RawStore
from lab.store.local import LocalFilesystemStore


class Miner(Protocol):
    corpus: str

    def acquire(
        self,
        config: MinerConfig,
        store: RawStore,
        checkpoint: Checkpoint,
    ) -> RunManifest: ...


def build_store() -> RawStore:
    backend = os.environ.get("RAW_STORE_BACKEND", "local").strip().lower()
    if backend == "gcs":
        from lab.store.gcs import GCSStore

        bucket = os.environ.get("GCS_BUCKET", "").strip()
        if not bucket:
            raise ValueError("GCS_BUCKET is required when RAW_STORE_BACKEND=gcs")
        prefix = os.environ.get("GCS_PREFIX", "raw/").strip()
        return GCSStore(bucket=bucket, prefix=prefix)
    root = os.environ.get("RAW_STORE_ROOT", "./storage").strip()
    return LocalFilesystemStore(root)


def build_checkpoint(corpus: str) -> Checkpoint:
    backend = os.environ.get("CHECKPOINT_BACKEND", "file").strip().lower()
    if backend == "redis":
        from lab.checkpoint.redis import RedisCheckpoint

        url = os.environ.get("CHECKPOINT_REDIS_URL", "").strip()
        if not url:
            raise ValueError("CHECKPOINT_REDIS_URL is required when CHECKPOINT_BACKEND=redis")
        return RedisCheckpoint(url=url, corpus=corpus)
    if backend == "memory":
        return InMemoryCheckpoint()
    root = os.environ.get("CHECKPOINT_ROOT", "./checkpoints").strip()
    return FileCheckpoint(root=root, corpus=corpus)


def manifest_root() -> Path:
    root = os.environ.get("MANIFEST_ROOT", "./manifests").strip()
    return Path(root)


def run_acquisition(
    miner_name: str,
    config: MinerConfig,
    *,
    store: RawStore | None = None,
    checkpoint: Checkpoint | None = None,
) -> RunManifest:
    """Single entry point for raw acquisition runs."""
    from lab.miners.registry import get_miner

    miner = get_miner(miner_name)
    store = store or build_store()
    checkpoint = checkpoint or build_checkpoint(miner.corpus)

    run_id = uuid.uuid4().hex[:12]
    manifest = RunManifest(
        run_id=run_id,
        corpus=miner.corpus,
        miner_name=miner_name,
        started_at=utc_now(),
        storage_prefix=store.storage_prefix,
    )

    try:
        result = miner.acquire(config, store, checkpoint)
        manifest.fetched = result.fetched
        manifest.skipped = result.skipped
        manifest.failed = result.failed
        manifest.errors = list(result.errors)
    except NotImplementedError:
        raise
    except Exception as exc:
        manifest.failed += 1
        manifest.errors.append(str(exc))
    finally:
        manifest.finished_at = utc_now()

    out_dir = manifest_root()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / f"{run_id}.json"
    manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    manifest.manifest_path = str(manifest_path.resolve())

    return manifest
