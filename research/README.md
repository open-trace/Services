# OpenTrace Research Lab

Raw data acquisition and storage for OpenTrace corpora. **No chunking, embedding, or Qdrant loading** — that stays in [ml-eng](https://github.com/open-trace/data-team/tree/main/ml-eng).

## Quickstart

```bash
cd research
pip install -e ".[dev]"
python -m lab.cli list
python -m lab.cli acquire arxiv \
  --query "all:agriculture OR all:crop" \
  --max-results 10 \
  --download-pdf
```

## Raw artifact layout

Every stored item follows:

```
storage/{corpus}/{source_id}/
  meta.json          # written by RawStore from miner metadata
  artifact.pdf       # or .json, .txt, .html — miner-specific
```

Run summaries:

```
manifests/{run_id}.json
```

Checkpoints (dedupe):

```
checkpoints/{corpus}.jsonl
```

## Corpus status

| Miner | Status | Notes |
|-------|--------|-------|
| `arxiv` | Implemented | Atom API + optional PDF download |
| `news` | Implemented | RSS feeds + trafilatura full-text extraction (10 countries) |
| `ugc` | Implemented | Agricultural blogs and extension service content |
| `youtube` | Stub | Agripreneur how-to transcripts |
| `manuals` | Stub | Practice manuals and textbooks |

## Configuration

Copy `../.env.example` to `.env` or export variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `RAW_STORE_BACKEND` | `local` | `local` or `gcs` |
| `RAW_STORE_ROOT` | `./storage` | Local storage root |
| `GCS_BUCKET` | — | Required for GCS backend |
| `CHECKPOINT_BACKEND` | `file` | `memory`, `file`, or `redis` |
| `CHECKPOINT_REDIS_URL` | — | When using redis checkpoint |

## Graduation to ml-eng

A corpus graduates when:

1. Sample quality eval passes (manual or scripted review)
2. Licensing and dedupe policy documented
3. Stable raw schema agreed with ml-eng ingestion owners
4. Ingestion path into Qdrant Cloud defined
5. Cost at target scale understood

Handoff: ml-eng reads from GCS bucket (`RAW_STORE_BACKEND=gcs`) or shared mount; no Python import coupling between repos.

## Architecture

Deep modules (see repo `.agents/skills/codebase-design/`):

- `run_acquisition()` — single entry point
- `RawStore` — local + GCS adapters
- `Checkpoint` — memory + file + redis adapters
- `Miner` — one adapter per corpus (`arxiv` first)

## Phase 2 (not in v1)

- Langfuse tracing for agentic miners
- Railway cron deploy for scheduled acquisition
