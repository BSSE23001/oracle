# Deployment (Supabase + Render + Vercel + GitHub Actions)

This phase takes everything running under `docker compose` locally and
puts it on the public internet: Supabase for Postgres, Render for the
FastAPI api + Celery worker, Vercel for the Next.js frontend, and GitHub
Actions wiring CI to both deploy targets so nothing ships unless tests
pass first.

**Cost note, upfront:** everything below fits in free tiers _except_ the
Celery worker, which Render does not offer on its free plan. Render Postgres also
free-tier-expires after 30 days, which is why this guide uses Supabase for
the database instead (matching the original spec's "PostgreSQL
(Supabase)"), Supabase's free Postgres doesn't expire, it just pauses
after a week of total inactivity and un-pauses on the next request.
Vercel's frontend hosting and Render's web service are both free for this
project's traffic level.

---

## 1. Supabase (Postgres)

1. Go to **https://supabase.com**, sign up, and click **New project**.
2. Pick an organization (create one if it's your first project), name the
   project `oracle`, generate a strong database password (save it, you
   need it for the connection string), and pick a region close to where
   you'll deploy Render (matching regions reduces latency between your
   API and database).
3. Wait ~2 minutes for provisioning, then go to **Project Settings →
   Database → Connection string**.
4. You need **two different connection strings** for this project, copy
   both now:
   - **Transaction pooler (port 6543)**, used by the FastAPI `api`
     service. Select "Transaction" mode in the dialog. Looks like:
     `postgresql://postgres.xxxxxxxx:[YOUR-PASSWORD]@aws-0-REGION.pooler.supabase.com:6543/postgres`
   - **Session pooler (port 5432)**, used by the Celery `worker` service
     (and for running Alembic migrations). Select "Session" mode instead.
     Same host, port `5432`.

   Why two different ones: the transaction pooler reassigns the
   underlying Postgres connection between every statement, which is
   exactly what a stateless web API wants (cheap, scalable, many short
   connections) but breaks long-lived usage like Celery task state and
   the LangGraph Postgres checkpointer. Session mode gives the worker a
   stable, dedicated connection instead.

5. Convert each to ORACLE's expected URL format by adding `+asyncpg`
   after `postgresql`:

   ```
   # api service DATABASE_URL (transaction pooler, port 6543):
   postgresql+asyncpg://postgres.xxxxxxxx:[YOUR-PASSWORD]@aws-0-REGION.pooler.supabase.com:6543/postgres

   # worker service DATABASE_URL (session pooler, port 5432):
   postgresql+asyncpg://postgres.xxxxxxxx:[YOUR-PASSWORD]@aws-0-REGION.pooler.supabase.com:5432/postgres
   ```

   (Both use the `+asyncpg` form even though the worker's sync code swaps
   it for `+psycopg` internally, `app/config.py`'s `database_url_sync`
   and `database_url_psycopg_raw` properties do that conversion
   automatically from whatever you put in `DATABASE_URL`.)

6. Run the migrations against your new database **once**, from your local
   machine, before the api/worker services come up for the first time:
   ```bash
   cd backend
   source .venv/bin/activate   # or just use your docker-compose Python env
   DATABASE_URL="postgresql+asyncpg://postgres.xxxxxxxx:[YOUR-PASSWORD]@aws-0-REGION.pooler.supabase.com:5432/postgres" \
     alembic upgrade head
   ```
   (Use the session-mode/5432 URL for this, migrations want a stable
   connection, same reasoning as the worker.)

---

## 2. Render (FastAPI api + Celery worker + Redis)

1. Go to **https://render.com** and sign up (GitHub sign-in is easiest,
   it also connects your repo access in the same step).
2. Push this repo to your own GitHub account if you haven't already.
3. Edit `render.yaml` at the repo root: replace
   `https://github.com/YOUR_GITHUB_USERNAME/oracle.git` (appears twice)
   with your actual fork's URL.
4. In the Render Dashboard: **New → Blueprint**, connect your repo, and
   Render will read `render.yaml` and propose three resources:
   `oracle-api` (web), `oracle-worker` (background worker), `oracle-redis`
   (Key Value). Click through to create them.
5. Render will prompt you for every `sync: false` environment variable
   during this flow, paste in:

   | Variable                               | Where to get it                                                                                                                                                    |
   | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
   | `OPENROUTER_API_KEY`                   | `docs/GET_API_KEYS.md` point 1                                                                                                                                     |
   | `OPENROUTER_MODELS`                    | same default as your local `.env` is fine                                                                                                                          |
   | `TAVILY_API_KEY`                       | `docs/GET_API_KEYS.md` point 2                                                                                                                                     |
   | `LANGSMITH_API_KEY`                    | `docs/GET_API_KEYS.md` point 3                                                                                                                                     |
   | `CROSSREF_MAILTO`                      | your own email                                                                                                                                                     |
   | `DATABASE_URL` (on `oracle-api`)       | the **port 6543** Supabase string from step 1                                                                                                                      |
   | `DATABASE_URL` (on `oracle-worker`)    | the **port 5432** Supabase string from step 1, these are deliberately different per service, Render lets you set the same env var key to a different value on each |
   | `CORS_ALLOW_ORIGINS` (on `oracle-api`) | leave as a placeholder for now, e.g. `https://oracle.vercel.app`, you'll get the real Vercel URL in step 3 and can update it then                                  |

6. Once both services finish their first (manually-triggered) deploy from
   the Blueprint, run the migrations against this same database if you
   haven't already, Render's Dashboard has a **Shell** tab on
   the `oracle-api` service if you'd rather run `alembic upgrade head`
   from inside the deployed container instead of locally.
7. Get each service's **deploy hook URL**: open `oracle-api` → **Settings**
   → scroll to **Deploy Hook** → copy the URL. Repeat for `oracle-worker`.
   You'll paste these into GitHub Actions secrets in step 4.
8. Note your `oracle-api` service's public URL (shown at the top of its
   dashboard page, looks like `https://oracle-api-xxxx.onrender.com`) —
   you need it for Vercel's `NEXT_PUBLIC_API_BASE_URL` in step 3.

---

## 3. Vercel (Next.js frontend)

1. Go to **https://vercel.com** and sign up (GitHub sign-in recommended).
2. Click **Add New → Project**, import your forked repo, and when asked
   for the **Root Directory**, set it to `frontend` (Vercel auto-detects
   Next.js once you do).
3. Under **Environment Variables**, add:
   - `NEXT_PUBLIC_API_BASE_URL` = your Render `oracle-api` URL from step
     2.8 (e.g. `https://oracle-api-xxxx.onrender.com`)
4. Click **Deploy**. First deploy takes ~2 minutes.
5. Once deployed, copy your project's production URL (e.g.
   `https://oracle.vercel.app`) and go back to Render's `oracle-api`
   service → **Environment** → update `CORS_ALLOW_ORIGINS` to that exact
   URL, then manually redeploy `oracle-api` once so the CORS change takes
   effect.
6. Get the two values GitHub Actions needs to deploy on your behalf:
   - **`VERCEL_TOKEN`**: Vercel Dashboard → your avatar → **Settings →
     Tokens → Create**. Scope it to your account, no expiry (or set one
     and rotate later).
   - **`VERCEL_ORG_ID`** and **`VERCEL_PROJECT_ID`**: easiest way to get
     both at once — install the Vercel CLI locally (`npm i -g vercel`),
     run `vercel link` inside `frontend/` and follow the prompts to link
     it to the project you just created; this writes
     `frontend/.vercel/project.json`, which contains both IDs in plain
     text. (That file is already in `frontend/.gitignore` — don't commit
     it, just copy the two values out of it.)

---

## 4. GitHub Actions secrets

In your GitHub repo: **Settings → Secrets and variables → Actions → New
repository secret**. Add all five:

| Secret name                 | Value         |
| --------------------------- | ------------- |
| `RENDER_DEPLOY_HOOK_API`    | from step 2.7 |
| `RENDER_DEPLOY_HOOK_WORKER` | from step 2.7 |
| `VERCEL_TOKEN`              | from step 3.6 |
| `VERCEL_ORG_ID`             | from step 3.6 |
| `VERCEL_PROJECT_ID`         | from step 3.6 |

That's it, push to `main`, and:

```
push to main
   → ci.yml runs (backend lint+test, frontend typecheck+build)
   → on success: deploy-backend.yml fires  → curls both Render deploy hooks
   → on success: deploy-frontend.yml fires → vercel pull/build/deploy --prod
```

Both deploy workflows are gated on `workflow_run` against `CI`, a broken
test or a failed build on `main` never reaches either deploy target.

---

## Verifying the deployed system end-to-end

```bash
# Health check
curl https://oracle-api-xxxx.onrender.com/health

# Kick off a real research run against your deployed backend
curl -X POST https://oracle-api-xxxx.onrender.com/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main approaches to retrieval-augmented generation?"}'
```

Then open `https://oracle.vercel.app` in a browser, start a query from the
landing page, and you should see the full live agent wire board, same
experience as local dev, just running on Supabase/Render/Vercel instead
of `docker compose`.

## Troubleshooting

- **Render web service is slow on first request**, free web services
  spin down after 15 minutes idle; the first request after that wakes it
  back up and takes 30-60 seconds. This is expected on the free plan, not
  a bug. Upgrade `oracle-api`'s plan in `render.yaml` if you need it
  always-warm.
- **Worker logs show Postgres connection errors mentioning prepared
  statements**, double-check the worker's `DATABASE_URL` is the
  **session-mode (5432)** string, not the transaction-mode (6543) one;
  mixing these up is the most common mistake here.
- **SSE stream connects but never gets the `plan_review_required` event**
  check `oracle-worker`'s logs in the Render Dashboard; if you see
  OpenRouter rate-limit warnings, see the "free models are rate-limited"
  note in `backend/README.md`.
- **CORS errors in the browser console**, confirm `CORS_ALLOW_ORIGINS`
  on `oracle-api` exactly matches your Vercel production URL (including
  `https://`, no trailing slash), and that you redeployed `oracle-api`
  after changing it.
