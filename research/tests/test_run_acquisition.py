from __future__ import annotations

from lab.checkpoint.memory import InMemoryCheckpoint
from lab.models import MinerConfig, RunManifest, utc_now
from lab.run import run_acquisition
from lab.store.local import LocalFilesystemStore


class FakeMiner:
    corpus = "fake"

    def acquire(self, config, store, checkpoint):
        manifest = RunManifest(
            run_id="",
            corpus=self.corpus,
            miner_name="fake",
            started_at=utc_now(),
            storage_prefix=store.storage_prefix,
        )
        for i in range(3):
            sid = f"item-{i}"
            if checkpoint.is_seen(sid):
                manifest.skipped += 1
                continue
            store.put(self.corpus, sid, "artifact.txt", b"body", {"index": i})
            checkpoint.mark_seen(sid)
            manifest.fetched += 1
        manifest.finished_at = utc_now()
        return manifest


def test_run_acquisition_with_injected_deps(tmp_path, monkeypatch):
    store = LocalFilesystemStore(tmp_path / "storage")
    checkpoint = InMemoryCheckpoint()
    manifest_root = tmp_path / "manifests"
    monkeypatch.setenv("MANIFEST_ROOT", str(manifest_root))

    import lab.miners.registry as registry

    registry.register("fake", FakeMiner)
    config = MinerConfig(max_results=10, download_pdf=False)

    manifest = run_acquisition("fake", config, store=store, checkpoint=checkpoint)

    assert manifest.fetched == 3
    assert manifest.skipped == 0
    assert manifest.failed == 0
    assert manifest.manifest_path
    assert (manifest_root / f"{manifest.run_id}.json").is_file()
