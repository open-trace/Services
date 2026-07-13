# Langfuse v3 on Railway

Self-hosted LLM/RAG observability for ml-eng and future research lab tracing.

**Full walkthrough:** [deploy-railway-walkthrough.md](deploy-railway-walkthrough.md) (Phase 2)

## Deploy

Use the [official Langfuse v3 Railway template](https://langfuse.com/self-hosting/deployment/railway):

https://langfuse.com/self-hosting/deployment/railway

The template provisions: `langfuse-web`, `langfuse-worker`, Postgres, ClickHouse, Redis (internal), MinIO.

## Post-deploy

1. Open the `langfuse-web` public URL.
2. Create admin account.
3. Create a project → copy **Public key** and **Secret key**.
4. On `langfuse-web` service, set:
   ```
   AUTH_DISABLE_SIGNUP=true
   ```
5. Confirm `CLICKHOUSE_CLUSTER_ENABLED=false` for single-node Railway.

## Wire to ml-eng

```
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://your-langfuse-web.up.railway.app
```

Tracing is optional — ml-eng no-ops when keys are absent.

## Sizing

ClickHouse needs ~8 GB RAM minimum for the full stack. Budget ~$30–80+/month depending on trace volume.

## Blob storage (production)

Template includes MinIO. For durability, consider Cloudflare R2 or GCS with S3-compatible credentials if blob upload errors occur.

## Timezone

Postgres and ClickHouse must run in **UTC** (Langfuse requirement).

## Security

- Lock signup after admin account (`AUTH_DISABLE_SIGNUP=true`).
- Langfuse internal services use private networking by default — only expose `langfuse-web` publicly.
