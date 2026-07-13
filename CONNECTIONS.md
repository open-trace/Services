# Connection matrix

How OpenTrace repos connect to self-hosted Services infrastructure.

## App Redis

| Consumer | Variable | Purpose |
|----------|----------|---------|
| ml-eng RAG API | `RAG_REDIS_URL` | Chat sessions, BQ/catalog caches |
| ml-eng Streamlit QA | `RAG_REDIS_URL` | Optional session continuity |
| research lab | `CHECKPOINT_REDIS_URL` | Optional URL dedupe across long mining runs |

**Same Railway project:** reference `${{Redis.REDIS_URL}}` in Railway variables.

**Different project / local dev:** enable TCP proxy on the Redis service or use `docker compose -f docker-compose.local.yml`.

## Langfuse

| Consumer | Variables |
|----------|-----------|
| ml-eng RAG API | `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` |
| ml-eng Streamlit QA | Same (optional) |
| research lab | Same (Phase 2 — tracing for agentic POCs) |

Create keys in Langfuse UI → Project settings. Set `AUTH_DISABLE_SIGNUP=true` after admin account creation.

## Research lab storage

| Variable | Default | When |
|----------|---------|------|
| `RAW_STORE_BACKEND` | `local` | `local` or `gcs` |
| `RAW_STORE_ROOT` | `./storage` | Local filesystem root |
| `GCS_BUCKET` | — | Required when backend is `gcs` |
| `GCS_PREFIX` | `raw/` | Object key prefix |
| `CHECKPOINT_BACKEND` | `file` | `memory`, `file`, or `redis` |
| `CHECKPOINT_REDIS_URL` | — | When checkpoint backend is `redis` |

## Handoff to ml-eng

Raw artifacts layout (no import coupling):

```
storage/{corpus}/{source_id}/
  meta.json
  artifact.{pdf,txt,json,...}
manifests/{run_id}.json
```

ml-eng ingestion reads from GCS bucket or shared mount when a corpus graduates from the lab.
