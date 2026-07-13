from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from lab.store.interface import StoredRef


def _sanitize_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return cleaned[:200] or "unknown"


class LocalFilesystemStore:
    """Persist raw artifacts under {root}/{corpus}/{source_id}/."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root).resolve()

    @property
    def storage_prefix(self) -> str:
        return self._root.as_uri()

    def _artifact_dir(self, corpus: str, source_id: str) -> Path:
        return self._root / _sanitize_segment(corpus) / _sanitize_segment(source_id)

    def exists(self, corpus: str, source_id: str) -> bool:
        meta_path = self._artifact_dir(corpus, source_id) / "meta.json"
        return meta_path.is_file()

    def put(
        self,
        corpus: str,
        source_id: str,
        filename: str,
        content: bytes,
        meta: dict,
    ) -> StoredRef:
        dest_dir = self._artifact_dir(corpus, source_id)
        dest_dir.mkdir(parents=True, exist_ok=True)

        safe_name = _sanitize_segment(filename) or "artifact.bin"
        artifact_path = dest_dir / safe_name
        artifact_path.write_bytes(content)

        meta_payload = {
            **meta,
            "corpus": corpus,
            "source_id": source_id,
            "artifact_filename": safe_name,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "bytes_written": len(content),
        }
        meta_path = dest_dir / "meta.json"
        meta_path.write_text(json.dumps(meta_payload, indent=2, ensure_ascii=False), encoding="utf-8")

        total_bytes = len(content) + meta_path.stat().st_size
        return StoredRef(
            corpus=corpus,
            source_id=source_id,
            uri=artifact_path.as_uri(),
            bytes_written=total_bytes,
        )
