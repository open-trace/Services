from __future__ import annotations

import json
from pathlib import Path

from lab.store.local import LocalFilesystemStore


def test_put_writes_meta_and_artifact(tmp_path: Path) -> None:
    store = LocalFilesystemStore(tmp_path)
    meta = {"title": "Test paper", "source": "test"}
    ref = store.put("arxiv", "2301.00001", "artifact.pdf", b"%PDF-1.4", meta)

    assert ref.corpus == "arxiv"
    assert ref.source_id == "2301.00001"
    assert store.exists("arxiv", "2301.00001")

    artifact_dir = tmp_path / "arxiv" / "2301.00001"
    assert (artifact_dir / "artifact.pdf").read_bytes() == b"%PDF-1.4"
    meta_json = json.loads((artifact_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta_json["title"] == "Test paper"
    assert meta_json["corpus"] == "arxiv"


def test_exists_false_for_missing(tmp_path: Path) -> None:
    store = LocalFilesystemStore(tmp_path)
    assert store.exists("arxiv", "missing") is False
