# Self-managed Qdrant on Railway

Shared vector DB for ml-eng RAG retrieval. Previously Qdrant Cloud (external);
now self-hosted here alongside App Redis and Langfuse.

**Full walkthrough:** [deploy-railway-walkthrough.md](deploy-railway-walkthrough.md)

## Deploy

1. Open your Railway project (e.g. `opentrace-infra`).
2. **New** → **Docker Image** → `qdrant/qdrant:v1.13.6`.
3. **Settings** → **Volumes** → add a volume mounted at `/qdrant/storage`.
4. **Variables**:
   ```
   QDRANT__SERVICE__API_KEY=<generate a strong secret>
   ```
5. Do **not** generate a public domain — ml-eng reaches it over private networking (see below). Only generate one temporarily if you need external access (e.g. for the Qdrant Cloud migration job, see below).

## Wire to ml-eng

On the RAG API service (data-team/ml-eng), same Railway **environment** as the `qdrant` service:

```
QDRANT_URL=http://qdrant.railway.internal:6333
QDRANT_API_KEY=<same secret as QDRANT__SERVICE__API_KEY>
QDRANT_COLLECTION_NEWS=news_data
QDRANT_COLLECTION_ACADEMIC_PAPERS=academic_papers
QDRANT_COLLECTION_POLICIES=policies
QDRANT_COLLECTION_PUBLIC_REPORTS=public_reports
QDRANT_COLLECTION_FORMATION=formation
QDRANT_COLLECTION_OTA_INSIGHTS=OTA_insights
```

Verify via RAG API `GET /ready` — should report Qdrant reachable.

## Migrating from Qdrant Cloud

If you're moving data off an existing Qdrant Cloud cluster, use the snapshot
migration job in this repo:

```bash
docker build -f Dockerfile.migrate-qdrant -t opentrace-qdrant-migrate:latest .
```

Deploy it as a **one-off** Railway service in the same environment as the new
`qdrant` service (so `QDRANT_URL=http://qdrant.railway.internal:6333`
resolves), with:

```
QDRANT_OLD_URL=https://<your-cluster>.qdrant.tech
QDRANT_OLD_API_KEY=<old Qdrant Cloud API key>

QDRANT_URL=http://qdrant.railway.internal:6333
QDRANT_API_KEY=<new API key>
```

Optional:

```
MIGRATE_COLLECTIONS=news_data,academic_papers,policies,public_reports,formation,OTA_insights
MIGRATE_VERIFY_ONLY=1   # compare point counts only, no transfer
```

It copies collections byte-for-byte via Qdrant's native snapshot API — no
re-embedding, no downtime on the source. The source instance is already
public, so no networking changes are needed there; the target is never
exposed publicly. Remove/stop the service once migration is verified.

## Local dev

```bash
docker compose -f docker-compose.local.yml up -d
```

Then:

```
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=<local-dev-key>
```

## Operations

- Attach a **volume** — without one, all vector data is lost on redeploy.
- The Docker image is **unmanaged** — you own backups, upgrades, and snapshot retention.
- Collections are created/populated by ml-eng ingestion jobs (data-team/ml-eng), not from this repo.
