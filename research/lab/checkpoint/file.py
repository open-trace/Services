from __future__ import annotations

from pathlib import Path


class FileCheckpoint:
    """Append-only JSONL of seen source IDs, one file per corpus."""

    def __init__(self, root: Path | str, corpus: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        safe_corpus = corpus.replace("/", "_").replace("\\", "_") or "default"
        self._path = self._root / f"{safe_corpus}.jsonl"
        self._seen: set[str] | None = None

    def _load(self) -> set[str]:
        if self._seen is not None:
            return self._seen
        seen: set[str] = set()
        if self._path.is_file():
            for line in self._path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    seen.add(line)
        self._seen = seen
        return seen

    def is_seen(self, source_id: str) -> bool:
        return source_id in self._load()

    def mark_seen(self, source_id: str) -> None:
        seen = self._load()
        if source_id in seen:
            return
        seen.add(source_id)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(source_id + "\n")
