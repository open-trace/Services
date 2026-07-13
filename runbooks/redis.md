# App Redis on Railway

Shared Redis for ml-eng sessions and optional research lab checkpoints.

**Full walkthrough:** [deploy-railway-walkthrough.md](deploy-railway-walkthrough.md) (Phase 1)

## Deploy

1. Open your Railway project (e.g. `opentrace-infra`).
2. **Ctrl/Cmd+K** → search **Redis** → add service.
3. Or use the [Redis template](https://docs.railway.com/databases/redis).

Railway auto-generates `REDIS_URL`, `REDISHOST`, `REDISPORT`, `REDISPASSWORD`.

## Wire to ml-eng

On the RAG API service (data-team/ml-eng):

```
RAG_REDIS_URL=${{Redis.REDIS_URL}}/0
RAG_SESSION_TTL_SECONDS=86400
RAG_CACHE_TTL_SECONDS=3600
```

Verify via RAG API `GET /ready` — should report redis connected.

## Wire to research lab (optional)

Use a separate DB index to avoid key collisions:

```
CHECKPOINT_BACKEND=redis
CHECKPOINT_REDIS_URL=${{Redis.REDIS_URL}}/1
```

## Cross-project access

Services in **other** Railway projects need TCP proxy:

1. Redis service → Settings → Networking → enable TCP Proxy.
2. Use the public host:port in connection strings with password.

## Local dev

```bash
docker compose -f docker-compose.local.yml up -d
```

Then:

```
RAG_REDIS_URL=redis://localhost:6379/0
CHECKPOINT_REDIS_URL=redis://localhost:6379/1
```

## Operations

- Attach a **volume** if session/checkpoint survival across redeploys matters.
- Templates are **unmanaged** — you own backups and upgrades.
- Do not share this Redis with Langfuse's internal Redis (separate instance inside Langfuse template).
