from __future__ import annotations

from pathlib import Path

from lab.checkpoint.file import FileCheckpoint


def test_file_checkpoint_persists_across_instances(tmp_path: Path) -> None:
    root = tmp_path / "checkpoints"
    cp1 = FileCheckpoint(root, "arxiv")
    assert cp1.is_seen("paper-1") is False
    cp1.mark_seen("paper-1")

    cp2 = FileCheckpoint(root, "arxiv")
    assert cp2.is_seen("paper-1") is True
    assert cp2.is_seen("paper-2") is False


def test_file_checkpoint_isolates_corpus(tmp_path: Path) -> None:
    root = tmp_path / "checkpoints"
    cp_arxiv = FileCheckpoint(root, "arxiv")
    cp_arxiv.mark_seen("id-1")

    cp_news = FileCheckpoint(root, "news")
    assert cp_news.is_seen("id-1") is False
