"""
NewsMiner — RSS feed harvest for African agricultural news.

Fetches articles from configured RSS feeds, extracts full text via trafilatura,
and stores raw artifacts (YAML front-matter + body) in the RawStore.

Usage:
    python -m lab.cli acquire news --max-results 100
    python -m lab.cli acquire news --extras '{"countries":["Nigeria","Ghana"],"dry_run":true}'
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import yaml

from lab.checkpoint.interface import Checkpoint
from lab.models import MinerConfig, RunManifest, utc_now
from lab.store.interface import RawStore

logger = logging.getLogger(__name__)

# Default feeds path (relative to this file)
_DEFAULT_FEEDS_PATH = Path(__file__).resolve().parent / "feeds" / "news_feeds.json"

_REQUEST_DELAY_S = 1.0  # default delay between article fetches
_USER_AGENT = "OpenTrace-Lab/0.1 (news-miner)"


def _source_id(url: str) -> str:
    """Deterministic short ID from article URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _parse_published(entry: Any) -> str | None:
    """Extract ISO date from feedparser entry."""
    pub = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if pub:
        try:
            return datetime(*pub[:6], tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return getattr(entry, "published", None) or getattr(entry, "updated", None)


def _extract_full_text(url: str) -> str | None:
    """Fetch and extract main article text using trafilatura."""
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            return text
    except Exception as exc:
        logger.debug("trafilatura extract failed for %s: %s", url, exc)
    return None


def _load_feeds(feeds_path: str | Path | None) -> dict[str, list[dict[str, str]]]:
    """Load {country: [{name, url}]} feeds JSON."""
    path = Path(feeds_path) if feeds_path else _DEFAULT_FEEDS_PATH
    if not path.exists():
        logger.warning("Feeds file not found: %s — using empty feeds", path)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _build_front_matter(entry: Any, country: str, feed_name: str) -> dict[str, Any]:
    """Build YAML-safe metadata dict from a feedparser entry."""
    url = getattr(entry, "link", "") or ""
    return {
        "id": _source_id(url),
        "url": url,
        "title": (getattr(entry, "title", "") or "").strip(),
        "country": country,
        "feed": feed_name,
        "published_at": _parse_published(entry),
        "domain": "news",
        "doc_kind": "news_article",
        "miner": "news",
        "acquired_at": utc_now().isoformat(),
    }


def _article_to_bytes(meta: dict[str, Any], body: str) -> bytes:
    """Encode article as YAML front-matter + body text (UTF-8)."""
    front = yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{front}---\n\n{body}\n".encode("utf-8")


class NewsMiner:
    corpus = "news"

    def acquire(
        self,
        config: MinerConfig,
        store: RawStore,
        checkpoint: Checkpoint,
    ) -> RunManifest:
        feeds_path = config.extras.get("feeds_path")
        countries_filter = config.extras.get("countries", [])
        dry_run = bool(config.extras.get("dry_run", False))
        delay = float(config.extras.get("request_delay", _REQUEST_DELAY_S))

        feeds = _load_feeds(feeds_path)
        if not feeds:
            raise ValueError(
                f"No feeds loaded. Place a feeds JSON at {_DEFAULT_FEEDS_PATH} "
                f"or pass extras['feeds_path']."
            )

        # Filter countries if specified
        if countries_filter:
            norm = {c.strip().lower() for c in countries_filter}
            feeds = {k: v for k, v in feeds.items() if k.strip().lower() in norm}

        manifest = RunManifest(
            run_id="",
            corpus=self.corpus,
            miner_name="news",
            started_at=utc_now(),
            storage_prefix=store.storage_prefix,
        )

        total_fetched = 0

        for country, country_feeds in feeds.items():
            for feed_info in country_feeds:
                feed_name = feed_info.get("name", "unknown")
                feed_url = feed_info.get("url", "")
                if not feed_url:
                    continue

                logger.info("Parsing feed: %s (%s)", feed_name, country)
                try:
                    parsed = feedparser.parse(feed_url, agent=_USER_AGENT)
                except Exception as exc:
                    manifest.failed += 1
                    manifest.errors.append(f"feed_parse:{feed_name}:{exc}")
                    continue

                for entry in parsed.entries:
                    if total_fetched >= config.max_results:
                        break

                    article_url = getattr(entry, "link", "") or ""
                    if not article_url:
                        continue

                    sid = _source_id(article_url)

                    if checkpoint.is_seen(sid) or store.exists(self.corpus, sid):
                        manifest.skipped += 1
                        continue

                    meta = _build_front_matter(entry, country, feed_name)

                    if dry_run:
                        logger.info("[DRY RUN] would fetch: %s", article_url)
                        manifest.skipped += 1
                        continue

                    try:
                        # Try full text extraction
                        body = _extract_full_text(article_url)
                        if not body:
                            # Fallback to RSS summary
                            body = (getattr(entry, "summary", "") or "").strip()
                            if body:
                                meta["body_source"] = "rss_summary"
                            else:
                                manifest.skipped += 1
                                continue
                        else:
                            meta["body_source"] = "trafilatura"

                        content = _article_to_bytes(meta, body)
                        store.put(self.corpus, sid, "article.txt", content, meta)
                        checkpoint.mark_seen(sid)
                        manifest.fetched += 1
                        total_fetched += 1

                        if delay > 0:
                            time.sleep(delay)

                    except Exception as exc:
                        manifest.failed += 1
                        manifest.errors.append(f"{sid}:{exc}")

                if total_fetched >= config.max_results:
                    break
            if total_fetched >= config.max_results:
                break

        manifest.finished_at = utc_now()
        return manifest
