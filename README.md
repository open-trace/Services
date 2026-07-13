# OpenTrace Services

Shared self-hosted infrastructure and the **research lab** for raw data acquisition.

This repo does **not** deploy application code (RAG API, chunking, Qdrant loaders). Those live in [data-team/ml-eng](https://github.com/open-trace/data-team/tree/main/ml-eng).

## Two halves

| Half | Purpose | Where |
|------|---------|--------|
| **Platform** | Redis, Langfuse, connection docs | Root docs + [runbooks/](runbooks/) |
| **Research lab** | Raw fetch + store only (no processing) | [research/](research/) |

## Platform (Railway)

**Start here:** [runbooks/deploy-railway-walkthrough.md](runbooks/deploy-railway-walkthrough.md) — step-by-step checklist for App Redis + Langfuse.

Deploy shared infra via Railway one-click templates:

- **App Redis** — [Railway Redis template](https://docs.railway.com/databases/redis) for ml-eng session storage (`RAG_REDIS_URL`) and optional research checkpoints (`CHECKPOINT_REDIS_URL`)
- **Langfuse v3** — [Official Langfuse Railway template](https://langfuse.com/self-hosting/deployment/railway) for LLM/RAG tracing

Langfuse ships with its **own** internal Redis, Postgres, ClickHouse, and MinIO. Do not point ml-eng or the research lab at Langfuse's Redis.

See [CONNECTIONS.md](CONNECTIONS.md) for the env var matrix across consumer repos.

Local Redis for dev: `docker compose -f docker-compose.local.yml up -d`

## Research lab

POC miners acquire raw corpora (papers, transcripts, manuals, news, UGC) and store artifacts under a documented layout. Processing and chunking happen in ml-eng after graduation.

```bash
cd research
pip install -e ".[dev]"
python -m lab.cli acquire arxiv --query "all:agriculture" --max-results 10 --download-pdf
```

See [research/README.md](research/README.md) for raw layout, graduation criteria, and corpus status.

## Consumer repos

| Repo | Uses from Services |
|------|-------------------|
| [ml-eng](https://github.com/open-trace/data-team/tree/main/ml-eng) | `RAG_REDIS_URL`, `LANGFUSE_*`, raw corpora from GCS after graduation |
| Other OpenTrace projects | Same platform vars; see CONNECTIONS.md |
