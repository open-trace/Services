from __future__ import annotations

import json
import re

from lab.store.interface import StoredRef


def _sanitize_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return cleaned[:200] or "unknown"


class GCSStore:
    """Persist raw artifacts to Google Cloud Storage."""

    def __init__(self, bucket: str, prefix: str = "raw/") -> None:
        from google.cloud import storage

        self._client = storage.Client()
        self._bucket_name = bucket
        self._prefix = prefix.rstrip("/") + "/" if prefix else ""

    @property
    def storage_prefix(self) -> str:
        return f"gs://{self._bucket_name}/{self._prefix}"

    def _object_prefix(self, corpus: str, source_id: str) -> str:
        return f"{self._prefix}{_sanitize_segment(corpus)}/{_sanitize_segment(source_id)}/"

    def exists(self, corpus: str, source_id: str) -> bool:
        bucket = self._client.bucket(self._bucket_name)
        blob = bucket.blob(f"{self._object_prefix(corpus, source_id)}meta.json")
        return blob.exists()

    def put(
        self,
        corpus: str,
        source_id: str,
        filename: str,
        content: bytes,
        meta: dict,
    ) -> StoredRef:
        from datetime import datetime, timezone

        bucket = self._client.bucket(self._bucket_name)
        base = self._object_prefix(corpus, source_id)
        safe_name = _sanitize_segment(filename) or "artifact.bin"

        artifact_blob = bucket.blob(f"{base}{safe_name}")
        artifact_blob.upload_from_string(content)

        meta_payload = {
            **meta,
            "corpus": corpus,
            "source_id": source_id,
            "artifact_filename": safe_name,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "bytes_written": len(content),
        }
        meta_bytes = json.dumps(meta_payload, indent=2, ensure_ascii=False).encode("utf-8")
        meta_blob = bucket.blob(f"{base}meta.json")
        meta_blob.upload_from_string(meta_bytes, content_type="application/json")

        uri = f"gs://{self._bucket_name}/{base}{safe_name}"
        return StoredRef(
            corpus=corpus,
            source_id=source_id,
            uri=uri,
            bytes_written=len(content) + len(meta_bytes),
        )
