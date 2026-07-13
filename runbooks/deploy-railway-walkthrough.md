# Railway deploy walkthrough — App Redis + Langfuse

Line-by-line checklist for deploying OpenTrace shared infrastructure on Railway and wiring it to [ml-eng](https://github.com/open-trace/data-team/tree/main/ml-eng).

**Estimated time:** Redis ~10 min · Langfuse ~30–45 min (first boot is slow)

See also: [redis.md](redis.md) · [langfuse.md](langfuse.md) · [CONNECTIONS.md](../CONNECTIONS.md)

---

## Before you start

- [ ] Railway account at [railway.com](https://railway.com)
- [ ] GitHub connected (for ml-eng services in the same project)
- [ ] Decide project name: **`opentrace-infra`** (recommended)

**Important:** You will have **two separate Redis instances**:

| Instance | Purpose | Used by |
|----------|---------|---------|
| **App Redis** | Sessions, caches, optional mining checkpoints | ml-eng, research lab |
| **Langfuse internal Redis** | Langfuse queues only | Langfuse template (do not reuse) |

---

## Phase 1 — Create project + App Redis

### 1.1 Create Railway project

- [ ] Go to [railway.com/new](https://railway.com/new)
- [ ] Create empty project named `opentrace-infra`

### 1.2 Add App Redis

**Option A — Command palette (recommended)**

- [ ] Open project canvas
- [ ] Press **Ctrl+K** (Windows) or **Cmd+K** (Mac)
- [ ] Type **Redis** → select **Add Redis**
- [ ] Wait until service status is **Running**

**Option B — Template**

- [ ] Open [Railway Redis docs](https://docs.railway.com/databases/redis)
- [ ] Deploy template into `opentrace-infra`

### 1.3 Confirm Redis variables

- [ ] Click **Redis** service → **Variables**
- [ ] Confirm these exist (auto-generated):
  - `REDIS_URL`
  - `REDISHOST`
  - `REDISPORT`
  - `REDISPASSWORD`

### 1.4 Add persistence (recommended)

- [ ] Redis service → **Settings** → **Volumes**
- [ ] Add volume (e.g. mount path `/data`)
- [ ] Redeploy if prompted

Without a volume, session data may be lost on redeploy.

### 1.5 Wire Redis to ml-eng RAG API

If ml-eng is not yet in this project, add it first:

- [ ] **New** → **GitHub Repo** → `open-trace/data-team`
- [ ] Set **Root Directory** to `ml-eng/`
- [ ] Config file: `railway.toml` (RAG API)

On the **RAG API** service → **Variables**:

```bash
RAG_REDIS_URL=${{Redis.REDIS_URL}}/0
RAG_SESSION_TTL_SECONDS=86400
RAG_CACHE_TTL_SECONDS=3600
```

Replace `Redis` with your Redis service name if Railway named it differently.

- [ ] Redeploy RAG API

### 1.6 Verify Redis

- [ ] Open RAG API public URL
- [ ] `GET /ready` — response should show redis connected
- [ ] Optional: send `POST /query` with a `session_id`; redeploy API; same `session_id` should retain context

### 1.7 Wire Redis to Streamlit QA (optional)

On the Streamlit service (`railway.streamlit.toml`):

```bash
RAG_REDIS_URL=${{Redis.REDIS_URL}}/0
```

### 1.8 Wire Redis to research lab (optional)

For long mining runs with Redis checkpoints:

```bash
CHECKPOINT_BACKEND=redis
CHECKPOINT_REDIS_URL=${{Redis.REDIS_URL}}/1
```

Use DB index `/1` so keys do not collide with ml-eng on `/0`.

### 1.9 Cross-project Redis (only if ml-eng is elsewhere)

- [ ] Redis service → **Settings** → **Networking** → enable **TCP Proxy**
- [ ] Build URL: `redis://default:<REDISPASSWORD>@<proxy-host>:<port>/0`

---

## Phase 2 — Deploy Langfuse v3

### 2.1 Deploy template

- [ ] Open [Langfuse Railway guide](https://langfuse.com/self-hosting/deployment/railway)
- [ ] Click **Deploy on Railway** (or [railway.com/deploy/langfuse](https://railway.com/deploy/langfuse))
- [ ] Select project **`opentrace-infra`**
- [ ] Confirm deploy

Railway creates 6 services:

| Service | Role |
|---------|------|
| `langfuse-web` | UI + API (public) |
| `langfuse-worker` | Background ingestion |
| Postgres | Transactional metadata |
| ClickHouse | Trace analytics (required v3) |
| Redis | Langfuse internal queue |
| MinIO | Blob storage |

- [ ] Wait for all services to reach **Running** (5–15 min on first boot)
- [ ] If `langfuse-worker` restarts repeatedly, wait — ClickHouse migrations can take >1 min

### 2.2 Confirm env vars

On **`langfuse-web`** → **Variables**:

- [ ] `CLICKHOUSE_CLUSTER_ENABLED=false` (required for single-node Railway)

### 2.3 Generate public URL

- [ ] `langfuse-web` → **Settings** → **Networking** → **Generate Domain** (if needed)
- [ ] Copy URL, e.g. `https://langfuse-web-production-xxxx.up.railway.app`

### 2.4 Create admin account

- [ ] Open Langfuse URL in browser
- [ ] Sign up with admin email/password
- [ ] Complete onboarding

Do this **before** locking signup (step 2.6).

### 2.5 Create project + API keys

- [ ] Langfuse UI → **New project** (e.g. `opentrace-rag`)
- [ ] **Project Settings** → **API Keys**
- [ ] Copy **Public key** (`pk-lf-...`) and **Secret key** (`sk-lf-...`)
- [ ] Store keys securely (Railway variables or secrets manager)

### 2.6 Lock down signup

- [ ] Railway → `langfuse-web` → **Variables** → add:

```bash
AUTH_DISABLE_SIGNUP=true
```

- [ ] Redeploy `langfuse-web`
- [ ] Confirm new users cannot self-register

### 2.7 Wire Langfuse to ml-eng

On **RAG API** service → **Variables**:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://your-langfuse-web.up.railway.app
```

Use the full `https://` URL for `LANGFUSE_HOST`.

- [ ] Redeploy RAG API
- [ ] Repeat on Streamlit QA if desired (optional tracing)

### 2.8 Verify tracing

- [ ] `POST /query` on RAG API with a sample question
- [ ] Langfuse UI → **Traces** — new trace should appear within seconds
- [ ] Trace should include LLM calls, retrieval, graph nodes

If keys are missing, ml-eng silently skips tracing (no error).

### 2.9 Sizing check

- [ ] ClickHouse service has adequate memory (≥8 GB recommended)
- [ ] Monitor Railway usage dashboard — budget ~$30–80+/month for full stack
- [ ] If UI is slow or OOM errors: increase memory on ClickHouse and `langfuse-web`

### 2.10 Blob storage (if upload errors)

If you see `Failed to upload events to blob storage`:

**Testing:** attach volume to Langfuse, set `LANGFUSE_STORAGE=local`

**Production:** use Cloudflare R2 or GCS with S3-compatible credentials:

```bash
BUCKET_NAME=your-bucket
S3_ENDPOINT=https://...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_REGION=auto
```

See [Railway Langfuse blob storage thread](https://station.railway.com/questions/lang-fuse-with-rail-way-issue-745a0a55).

---

## Phase 3 — Final checklist

### ml-eng RAG API variables

| Variable | Value |
|----------|-------|
| `RAG_REDIS_URL` | `${{Redis.REDIS_URL}}/0` |
| `RAG_SESSION_TTL_SECONDS` | `86400` |
| `RAG_CACHE_TTL_SECONDS` | `3600` |
| `LANGFUSE_PUBLIC_KEY` | `pk-lf-...` |
| `LANGFUSE_SECRET_KEY` | `sk-lf-...` |
| `LANGFUSE_HOST` | `https://...up.railway.app` |

Plus existing ml-eng vars: `QDRANT_*`, `RAG_LLM_*`, `BQ_*`, `GOOGLE_APPLICATION_CREDENTIALS_BASE64`, etc.

### Verification

- [ ] `GET /health` on RAG API — 200
- [ ] `GET /ready` on RAG API — redis connected
- [ ] Langfuse UI loads and shows traces after `/query`
- [ ] `AUTH_DISABLE_SIGNUP=true` on Langfuse
- [ ] App Redis has volume attached (if durability required)

### Deploy order (reference)

```
Create project → App Redis → wire ml-eng → verify /ready
             → Langfuse template → admin + keys → lock signup
             → wire LANGFUSE_* → verify traces
```

---

## Local dev parity

From repo root:

```bash
docker compose -f docker-compose.local.yml up -d
```

Local variables:

```bash
RAG_REDIS_URL=redis://localhost:6379/0
CHECKPOINT_REDIS_URL=redis://localhost:6379/1
```

For Langfuse locally, most teams either point at the Railway instance or skip tracing during local dev.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `/ready` shows redis disconnected | Wrong `RAG_REDIS_URL` or Redis not in same project | Check variable reference and service name |
| Sessions lost on redeploy | No Redis volume | Attach volume to App Redis |
| Langfuse worker restart loop | ClickHouse still migrating | Wait 2–5 min; check ClickHouse logs |
| Langfuse 500 on trace upload | Blob storage misconfigured | See step 2.10 |
| No traces in Langfuse | Missing/wrong `LANGFUSE_*` keys | Verify keys and `LANGFUSE_HOST` URL |
| Langfuse UI very slow | ClickHouse under-resourced | Increase ClickHouse memory |

---

## What stays external

These are **not** deployed from this repo:

| Service | Where |
|---------|-------|
| Qdrant | Qdrant Cloud (`QDRANT_URL`) |
| BigQuery | GCP |
| OpenRouter / Cohere | Managed API keys |
| ml-eng app code | [data-team/ml-eng](https://github.com/open-trace/data-team/tree/main/ml-eng) |
