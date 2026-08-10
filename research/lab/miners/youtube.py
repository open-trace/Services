"""
YoutubeMiner — African agricultural practice video transcripts (ML-033).
doc_kind: ``agricultural_practise`` (matches formation Qdrant collection ML-036)

Requires:
    YOUTUBE_API_KEY env var — YouTube Data API v3 key (free quota: 10k units/day)
    pip install youtube-transcript-api google-api-python-client

Usage:
    YOUTUBE_API_KEY=AIza... python -m lab.cli acquire youtube --max-results 50
    python -m lab.cli acquire youtube --extras '{"dry_run":true}'
    python -m lab.cli acquire youtube --extras '{"queries":["maize farming Kenya"]}'
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

import yaml

from lab.checkpoint.interface import Checkpoint
from lab.models import MinerConfig, RunManifest, utc_now
from lab.store.interface import RawStore

logger = logging.getLogger(__name__)


class _StubMiner:
    """Base for unimplemented miners. Raises NotImplementedError on acquire()."""

    corpus: str
    _name: str
    _poc_note: str

    def __init__(self, corpus: str, name: str, poc_note: str) -> None:
        self.corpus = corpus
        self._name = name
        self._poc_note = poc_note

    def acquire(
        self,
        config: MinerConfig,
        store: RawStore,
        checkpoint: Checkpoint,
    ) -> RunManifest:
        raise NotImplementedError(
            f"{self._name} miner is not implemented yet. POC scope: {self._poc_note}"
        )


_DEFAULT_CHANNELS_PATH = Path(__file__).resolve().parent / "feeds" / "youtube_channels.json"
_YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_YT_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
_REQUEST_DELAY_S = 0.5
_MAX_TRANSCRIPT_CHARS = 80_000  # ~20k tokens


def _stable_id(vid_id: str) -> str:
    """Deterministic short ID from YouTube video ID."""
    return hashlib.sha256(vid_id.encode()).hexdigest()[:16]


def _search_videos(
    api_key: str,
    query: str,
    *,
    channel_id: str | None = None,
    max_results: int = 25,
) -> list[dict[str, Any]]:
    """Search YouTube Data API v3. Returns raw items list or [] on failure."""
    try:
        import httpx
    except ImportError:
        logger.error("httpx not installed — cannot call YouTube Data API")
        return []

    params: dict[str, Any] = {
        "part": "snippet",
        "type": "video",
        "q": query,
        "maxResults": min(max_results, 50),
        "key": api_key,
        "relevanceLanguage": "en",
        "videoCaption": "closedCaption",
    }
    if channel_id:
        params["channelId"] = channel_id
    try:
        resp = httpx.get(_YT_SEARCH_URL, params=params, timeout=20.0)
        if resp.status_code != 200:
            logger.warning("YouTube search %s for query=%r: %s", resp.status_code, query, resp.text[:200])
            return []
        return resp.json().get("items") or []
    except Exception as exc:
        logger.warning("YouTube search failed query=%r: %s", query, exc)
        return []


def _get_video_details(api_key: str, video_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Batch-fetch snippet+contentDetails for up to 50 video IDs."""
    if not video_ids:
        return {}
    try:
        import httpx
    except ImportError:
        return {}
    try:
        resp = httpx.get(
            _YT_VIDEO_URL,
            params={"part": "snippet,contentDetails", "id": ",".join(video_ids[:50]), "key": api_key},
            timeout=20.0,
        )
        if resp.status_code != 200:
            return {}
        return {item["id"]: item for item in (resp.json().get("items") or [])}
    except Exception as exc:
        logger.warning("Video details failed: %s", exc)
        return {}


def _fetch_transcript(video_id: str) -> str | None:
    """Fetch caption text via youtube-transcript-api. Returns None when unavailable."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            NoTranscriptFound,
            TranscriptsDisabled,
            VideoUnavailable,
        )
    except ImportError:
        logger.error("youtube-transcript-api not installed — pip install youtube-transcript-api")
        return None
    try:
        tl = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            t = tl.find_transcript(["en"])
        except Exception:
            try:
                t = tl.find_generated_transcript(["en"])
            except Exception:
                t = next(iter(tl), None)
                if t is None:
                    return None
        text = " ".join(e.get("text", "") for e in t.fetch()).strip()
        return text[:_MAX_TRANSCRIPT_CHARS] if text else None
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as exc:
        logger.debug("No transcript %s: %s", video_id, exc)
        return None
    except Exception as exc:
        logger.warning("Transcript fetch failed %s: %s", video_id, exc)
        return None


def _load_channels(path: str | Path | None) -> list[dict[str, str]]:
    """Load [{name, channel_id, country, query}] seed config."""
    p = Path(path) if path else _DEFAULT_CHANNELS_PATH
    if not p.exists():
        logger.warning("YouTube channels file not found: %s — using empty list", p)
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def _build_front_matter(
    video_id: str,
    snippet: dict[str, Any],
    country: str,
    channel_name: str,
) -> dict[str, Any]:
    return {
        "id": _stable_id(video_id),
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": (snippet.get("title") or "").strip(),
        "description": (snippet.get("description") or "").strip()[:500],
        "country": country,
        "channel": snippet.get("channelTitle") or channel_name,
        "published_at": snippet.get("publishedAt") or snippet.get("publishTime"),
        "domain": "formation",
        "doc_kind": "agricultural_practise",
        "miner": "youtube",
        "acquired_at": utc_now().isoformat(),
    }


def _artifact_to_bytes(meta: dict[str, Any], transcript: str) -> bytes:
    front = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{front}---\n\n{transcript}\n".encode("utf-8")


class YoutubeMiner:
    """Mine YouTube agri-practice videos for the formation Qdrant collection.

    extras (MinerConfig.extras):
        channels_path  — path to youtube_channels.json override
        queries        — list of extra search query strings
        dry_run        — bool; log but do not store
        delay          — float; seconds between transcript fetches (default 0.5)
        api_key        — YouTube Data API key override (default: YOUTUBE_API_KEY env var)
    """

    corpus = "youtube"

    def acquire(self, config: MinerConfig, store: RawStore, checkpoint: Checkpoint) -> RunManifest:
        import os

        extras = config.extras or {}
        dry_run: bool = bool(extras.get("dry_run", False))
        delay: float = float(extras.get("delay", _REQUEST_DELAY_S))
        channels_path = extras.get("channels_path")
        extra_queries: list[str] = list(extras.get("queries") or [])
        api_key: str = str(extras.get("api_key") or os.environ.get("YOUTUBE_API_KEY", "")).strip()

        if not api_key:
            raise ValueError(
                "YOUTUBE_API_KEY env var is required. "
                "Get a free key at https://console.cloud.google.com (YouTube Data API v3)."
            )

        channels = _load_channels(channels_path)

        # Work items: (query, channel_id_or_None, country, channel_name)
        work_items: list[tuple[str, str | None, str, str]] = []
        for ch in channels:
            q = ch.get("query") or ""
            cid = ch.get("channel_id") or None
            country = ch.get("country") or "Unknown"
            name = ch.get("name") or cid or "unknown"
            if q or cid:
                work_items.append((q, cid, country, name))
        for q in extra_queries:
            work_items.append((q, None, "Unknown", "adhoc"))

        manifest = RunManifest(
            run_id="",
            corpus=self.corpus,
            miner_name="youtube",
            started_at=utc_now(),
            storage_prefix=store.storage_prefix,
        )
        total_fetched = 0

        for query, channel_id, country, channel_name in work_items:
            if total_fetched >= config.max_results:
                break

            remaining = config.max_results - total_fetched
            logger.info("Searching YouTube: query=%r channel=%s country=%s", query, channel_id or "(any)", country)

            items = _search_videos(api_key, query, channel_id=channel_id, max_results=min(remaining, 25))
            if not items:
                continue

            vid_ids = [
                i["id"]["videoId"]
                for i in items
                if isinstance(i.get("id"), dict) and i["id"].get("videoId")
            ]
            details = _get_video_details(api_key, vid_ids) if vid_ids else {}

            for item in items:
                if total_fetched >= config.max_results:
                    break

                raw_id = item.get("id") or {}
                vid_id = raw_id.get("videoId") or "" if isinstance(raw_id, dict) else str(raw_id)
                if not vid_id:
                    continue

                sid = _stable_id(vid_id)
                if checkpoint.is_seen(sid) or store.exists(self.corpus, sid):
                    manifest.skipped += 1
                    continue

                search_snippet = item.get("snippet") or {}
                detail_snippet = (details.get(vid_id) or {}).get("snippet") or {}
                snippet = {**search_snippet, **detail_snippet}
                meta = _build_front_matter(vid_id, snippet, country, channel_name)

                if dry_run:
                    logger.info("[DRY RUN] would fetch: %s  %s", vid_id, snippet.get("title", ""))
                    manifest.skipped += 1
                    continue

                try:
                    transcript = _fetch_transcript(vid_id)
                    if not transcript:
                        manifest.skipped += 1
                        continue

                    content = _artifact_to_bytes(meta, transcript)
                    store.put(self.corpus, sid, "transcript.txt", content, meta)
                    checkpoint.mark_seen(sid)
                    manifest.fetched += 1
                    total_fetched += 1
                    logger.info("Stored: %s  %s  (%d chars)", vid_id, snippet.get("title", ""), len(transcript))

                    if delay > 0:
                        time.sleep(delay)

                except Exception as exc:
                    manifest.failed += 1
                    manifest.errors.append(f"{vid_id}:{exc}")
                    logger.warning("Failed %s: %s", vid_id, exc)

        manifest.finished_at = utc_now()
        return manifest

