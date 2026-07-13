from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class MinerConfig:
    """Parameters for a single acquisition run. Corpus-specific keys live in extras."""

    max_results: int = 100
    download_pdf: bool = True
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunManifest:
    run_id: str
    corpus: str
    miner_name: str
    started_at: datetime
    finished_at: datetime | None = None
    fetched: int = 0
    skipped: int = 0
    failed: int = 0
    storage_prefix: str = ""
    manifest_path: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "corpus": self.corpus,
            "miner_name": self.miner_name,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "fetched": self.fetched,
            "skipped": self.skipped,
            "failed": self.failed,
            "storage_prefix": self.storage_prefix,
            "manifest_path": self.manifest_path,
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunManifest:
        started = data.get("started_at")
        finished = data.get("finished_at")
        return cls(
            run_id=str(data["run_id"]),
            corpus=str(data["corpus"]),
            miner_name=str(data["miner_name"]),
            started_at=datetime.fromisoformat(started) if isinstance(started, str) else utc_now(),
            finished_at=datetime.fromisoformat(finished) if isinstance(finished, str) else None,
            fetched=int(data.get("fetched", 0)),
            skipped=int(data.get("skipped", 0)),
            failed=int(data.get("failed", 0)),
            storage_prefix=str(data.get("storage_prefix", "")),
            manifest_path=str(data.get("manifest_path", "")),
            errors=list(data.get("errors") or []),
        )
