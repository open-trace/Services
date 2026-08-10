"""Unit tests for YoutubeMiner (ML-033) — fully mocked, no network calls."""
from __future__ import annotations
from unittest import mock
import pytest
from lab.checkpoint.memory import InMemoryCheckpoint
from lab.miners.youtube import YoutubeMiner, _artifact_to_bytes, _build_front_matter, _stable_id
from lab.models import MinerConfig
from lab.store.local import LocalFilesystemStore

_CH = [{"name": "FarmersTrend", "channel_id": "UC123", "country": "Kenya", "query": "maize farming"}]

def _item(vid_id, title="Test Video"):
    return {"id": {"kind": "youtube#video", "videoId": vid_id}, "snippet": {"title": title, "description": "desc", "channelTitle": "CH", "publishedAt": "2024-01-01T00:00:00Z"}}

def _store(tmp_path):
    return LocalFilesystemStore(str(tmp_path / "storage"))

def test_stable_id_deterministic():
    assert _stable_id("abc") == _stable_id("abc")
    assert _stable_id("abc") != _stable_id("xyz")
    assert len(_stable_id("abc")) == 16

def test_build_front_matter_fields():
    meta = _build_front_matter("abc123", {"title": "Maize", "description": "d", "channelTitle": "CH", "publishedAt": "2024-01-01T00:00:00Z"}, "Kenya", "CH")
    assert meta["doc_kind"] == "agricultural_practise"
    assert meta["domain"] == "formation"
    assert meta["miner"] == "youtube"
    assert meta["url"] == "https://www.youtube.com/watch?v=abc123"
    assert "acquired_at" in meta

def test_artifact_to_bytes():
    b = _artifact_to_bytes({"doc_kind": "agricultural_practise"}, "Hello transcript.")
    t = b.decode("utf-8")
    assert t.startswith("---\n")
    assert "agricultural_practise" in t
    assert "Hello transcript" in t

def test_acquire_stores_transcript(tmp_path):
    with mock.patch("lab.miners.youtube._search_videos", return_value=[_item("v001")]), \
         mock.patch("lab.miners.youtube._get_video_details", return_value={}), \
         mock.patch("lab.miners.youtube._fetch_transcript", return_value="Plant maize."), \
         mock.patch("lab.miners.youtube._load_channels", return_value=_CH):
        m = YoutubeMiner().acquire(MinerConfig(max_results=5, extras={"api_key": "k"}), _store(tmp_path), InMemoryCheckpoint())
    assert m.fetched == 1
    assert m.failed == 0

def test_acquire_skips_already_seen(tmp_path):
    cp = InMemoryCheckpoint()
    cp.mark_seen(_stable_id("v001"))
    with mock.patch("lab.miners.youtube._search_videos", return_value=[_item("v001")]), \
         mock.patch("lab.miners.youtube._get_video_details", return_value={}), \
         mock.patch("lab.miners.youtube._fetch_transcript") as mf, \
         mock.patch("lab.miners.youtube._load_channels", return_value=_CH):
        m = YoutubeMiner().acquire(MinerConfig(max_results=5, extras={"api_key": "k"}), _store(tmp_path), cp)
    assert m.skipped == 1
    assert m.fetched == 0
    mf.assert_not_called()

def test_acquire_skips_no_transcript(tmp_path):
    with mock.patch("lab.miners.youtube._search_videos", return_value=[_item("v002")]), \
         mock.patch("lab.miners.youtube._get_video_details", return_value={}), \
         mock.patch("lab.miners.youtube._fetch_transcript", return_value=None), \
         mock.patch("lab.miners.youtube._load_channels", return_value=_CH):
        m = YoutubeMiner().acquire(MinerConfig(max_results=5, extras={"api_key": "k"}), _store(tmp_path), InMemoryCheckpoint())
    assert m.fetched == 0
    assert m.skipped == 1

def test_acquire_dry_run(tmp_path):
    with mock.patch("lab.miners.youtube._search_videos", return_value=[_item("v003")]), \
         mock.patch("lab.miners.youtube._get_video_details", return_value={}), \
         mock.patch("lab.miners.youtube._fetch_transcript") as mf, \
         mock.patch("lab.miners.youtube._load_channels", return_value=_CH):
        m = YoutubeMiner().acquire(MinerConfig(max_results=5, extras={"api_key": "k", "dry_run": True}), _store(tmp_path), InMemoryCheckpoint())
    assert m.fetched == 0
    assert m.skipped == 1
    mf.assert_not_called()

def test_acquire_raises_without_api_key(tmp_path):
    with mock.patch("lab.miners.youtube._load_channels", return_value=[]):
        with pytest.raises(ValueError, match="YOUTUBE_API_KEY"):
            YoutubeMiner().acquire(MinerConfig(max_results=5, extras={}), _store(tmp_path), InMemoryCheckpoint())

def test_acquire_respects_max_results(tmp_path):
    items = [_item(f"v{i:03d}") for i in range(10)]
    tr = {f"v{i:03d}": f"t{i}" for i in range(10)}
    with mock.patch("lab.miners.youtube._search_videos", return_value=items), \
         mock.patch("lab.miners.youtube._get_video_details", return_value={}), \
         mock.patch("lab.miners.youtube._fetch_transcript", side_effect=lambda v: tr.get(v)), \
         mock.patch("lab.miners.youtube._load_channels", return_value=_CH):
        m = YoutubeMiner().acquire(MinerConfig(max_results=3, extras={"api_key": "k", "delay": 0}), _store(tmp_path), InMemoryCheckpoint())
    assert m.fetched == 3
