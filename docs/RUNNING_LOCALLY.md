# Running ORACLE locally without Docker

Two modes depending on how much of the stack you want:

| Mode | What you get | What you need |
|---|---|---|
| **A — CLI only** | Terminal-based research, no web UI | Python 3.12 + the 3 API keys you already have |
| **B — Full web app** | Browser UI, live agent panel, history | Python 3.12 + Supabase (you have it) + Upstash Redis (free, 5 min setup) |

---

## Mode A — CLI only (`run_local.py`)

No Redis, no Postgres, no FastAPI needed. Runs the entire agent graph
directly in your terminal using SQLite for the interrupt checkpoint.

### 1. Python environment

```bash
cd backend
python3.12 -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# macOS/Linux:
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 2. `.env` file

```bash
cp .env.example .env
```

Open `.env` and set these (leave everything else as the defaults):

```
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY
TAVILY_API_KEY=tvly-YOUR_KEY
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_YOUR_KEY

# SQLite checkpointer — no Postgres needed for CLI mode
CHECKPOINTER_BACKEND=sqlite
```

### 3. Run

```bash
python run_local.py "How effective are GLP-1 drugs for long-term weight maintenance?"
```

The terminal will:
1. Show the proposed research plan
2. Ask you to approve or request changes (type y/n)
3. Run all agents and print the final report with citations

---

## Mode B — Full web app (FastAPI + Next.js)

### What you need that you don't have yet: Redis

You already have Supabase (Postgres). The only missing piece is **Redis**,
which Celery uses as its task queue. The easiest free option — no
installation required — is **Upstash Redis** (free tier: 10,000
commands/day, plenty for development).

#### Get Upstash Redis (5 minutes)

1. Go to **https://upstash.com** and sign up (GitHub login works).
2. Click **Create Database** → choose **Regional** (pick the region
   closest to your Supabase region) → **Free tier** → Create.
3. In the database dashboard, click the **Connect** tab.
4. Copy the **Redis URL** — it looks like:
   ```
   rediss://default:AAABxxxxxx@careful-turtle-12345.upstash.io:6379
   ```
   Note the `rediss://` prefix (double-s) — that means TLS, which Upstash
   requires. Keep it exactly as-is.

#### Configure `.env`

Open `backend/.env` and set:

```env
# ── LLM, search, observability (you already have these) ──
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY
TAVILY_API_KEY=tvly-YOUR_KEY
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_YOUR_KEY

# ── Postgres: Supabase session pooler (port 5432, NOT 6543) ──────────
# In your Supabase project: Settings → Database → Connection string
# Choose "Session" mode, port 5432. Add +asyncpg after postgresql:
DATABASE_URL=postgresql+asyncpg://postgres.xxxxxxxx:YOUR_PASSWORD@aws-0-YOUR_REGION.pooler.supabase.com:5432/postgres
CHECKPOINTER_BACKEND=postgres

# ── Redis: Upstash (paste the URL you copied above) ──────────────────
REDIS_URL=rediss://default:YOUR_TOKEN@your-db.upstash.io:6379
CELERY_BROKER_URL=rediss://default:YOUR_TOKEN@your-db.upstash.io:6379
CELERY_RESULT_BACKEND=rediss://default:YOUR_TOKEN@your-db.upstash.io:6379

# ── CORS: allow the local Next.js dev server ──────────────────────────
CORS_ALLOW_ORIGINS=http://localhost:3000
```

> **Two different Supabase connection strings:** The `api` service
> (FastAPI) uses the **Transaction pooler** (port **6543**) for short
> web-request connections; the Celery **worker** uses the **Session
> pooler** (port **5432**) for longer-lived connections. For local
> development, using the session pooler (5432) for both is fine.

#### Run database migrations (once)

```bash
cd backend
source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt   # if you haven't already

alembic upgrade head
```

You should see Alembic print 4 table names (research_sessions,
research_reports, agent_events, feedback). This only needs to be done
once — re-running it when tables already exist is safe (it's a no-op).

#### Start the backend — TWO terminals

**Terminal 1 — FastAPI API server:**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

You should see `Uvicorn running on http://127.0.0.1:8000`. Visit
`http://localhost:8000/health` — it should return `{"status":"ok"}`.

**Terminal 2 — Celery worker:**

```bash
cd backend
source .venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
```

You should see `celery@... ready.` and the two registered tasks
(`oracle.run_research`, `oracle.resume_research`).

#### Start the frontend — Terminal 3

```bash
cd frontend
cp .env.example .env.local     # creates .env.local with defaults
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 is already correct
npm install
npm run dev
```

Open **http://localhost:3000**. The full ORACLE UI should load.

---

## Verifying everything is connected

1. **Backend health:** `curl http://localhost:8000/health` → `{"status":"ok"}`
2. **Start a research run** in the browser at http://localhost:3000
3. **Watch Terminal 2 (Celery)** — you should see:
   ```
   [INFO] Task oracle.run_research[...] received
   [INFO] Connecting checkpointer to Postgres: ...
   [INFO] PostgresSaver ready.
   [INFO] HTTP Request: POST https://openrouter.ai/...
   ```
4. **Plan review** — the browser will show the plan and ask you to approve it
5. After approving, watch for:
   ```
   [PARALLEL] Dispatching 3 specialist agents simultaneously → web_search(t1), ...
   [PARALLEL] Agent web_search_agent done — subtask t1, confidence 85%
   ```

---

## Troubleshooting

**`alembic upgrade head` fails with connection error**
→ Double-check your `DATABASE_URL` in `.env` uses `postgresql+asyncpg://`
(not `postgresql://`) and the correct Supabase session-pooler host and
password. Supabase passwords sometimes contain special characters — if
yours does, URL-encode them (e.g. `@` → `%40`).

**Celery worker crashes with `redis.exceptions.ConnectionError`**
→ Verify your `CELERY_BROKER_URL` is the Upstash URL with the `rediss://`
prefix (double-s). Standard `redis://` (single-s, no TLS) will be
rejected by Upstash.

**`ModuleNotFoundError: No module named 'psycopg'`**
→ Run `pip install 'psycopg[binary]'` — it's in `requirements.txt` but
sometimes pip skips it due to the extras bracket syntax. Or run
`pip install -r requirements.txt --force-reinstall`.

**OpenRouter 429 rate-limit warnings in worker logs**
→ Normal — the fallback to the next free model handles it automatically.
If all models keep returning 429, wait 60 seconds and try again. You can
also add a credit card to Upstash for higher rate limits (your actual
model calls are still free; the card just unlocks higher throughput).

**Frontend shows no data / SSE connection fails**
→ Check that `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` is in
`frontend/.env.local` (not `.env`) and that the FastAPI server in
Terminal 1 is running. Also make sure there's no corporate firewall
blocking localhost connections between ports.

**`KeyError: './data/chroma'`** (should be fixed, but just in case)
→ This was a thread-safety bug in Chroma initialisation. Make sure you're
running the latest code from this repo which uses the double-checked lock
pattern in `app/tools/vector_store.py`.
