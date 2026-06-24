# Frontend (Next.js)

The frontend is a Next.js 16 app that connects to the FastAPI
backend over HTTP + Server-Sent Events. No addition al accounts or API
keys are needed, it talks only to your own backend.

## Prerequisites

- Node.js 22 LTS (or 20 LTS)
- The backend running at `http://localhost:8000`
  (either `docker compose up` or bare-metal `uvicorn app.main:app`
  - a separate `celery -A app.tasks.celery_app worker` process)

If you don't have Node 22, install it via:

```bash
# macOS/Linux (via nvm)
nvm install 22 && nvm use 22

# or download from https://nodejs.org/en/download
```

## Install and run

```bash
cd frontend
cp .env.example .env.local        # default NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 is fine for local dev
npm install
npm run dev
```

The app is now at **http://localhost:3000**.

## Page structure

```
/                       Landing page, query input form + example prompts
/research/[sessionId]   Live research session:
                          - Supervisor planning phase (spinner + status label)
                          - Plan review card (approve or send feedback for revision)
                          - Agent wire board (parallel specialist lanes, live confidence)
                          - Report view (sections, fact-check appendix, citations, gauge)
                          - Feedback form (1-5 rating + optional comment)
/history                List of all past sessions with status tags and confidence scores
```

## How the real-time streaming works in the browser

When you navigate to `/research/[sessionId]`, the page mounts a
`useResearchStream` hook (in `lib/useResearchStream.ts`) that opens a
native browser `EventSource` to `GET /api/research/{sessionId}/stream`.

The backend (FastAPI) first replays every event already logged to the
`agent_events` Postgres table for that session (so refreshing mid-run or
reopening a tab after it finishes both give the full history), then
forwards live Redis pub/sub messages as they arrive from the Celery
worker. The hook processes each event through a pure reducer function and
returns a single `ResearchStreamState` object to the page, no external
state library needed.

The key events, in order:

| Event                               | What the UI shows                                       |
| ----------------------------------- | ------------------------------------------------------- |
| `session_started`                   | Status label updates to "Supervisor decomposing query…" |
| `plan_review_required`              | Plan review card appears with Approve / Request changes |
| `plan_decision_received` (approved) | Wire board appears; all lanes show as "running"         |
| `node_update` (specialist agents)   | Each lane card flips to "done" with its summary         |
| `node_update` (synthesis)           | Status label → "Synthesizing…"                          |
| `node_update` (fact_check_pass)     | Status label → "Fact-checking…"                         |
| `session_completed`                 | Report view appears, wire board remains for reference   |

## Building for production

```bash
npm run build
npm start
```

Or deploy to Vercel. Vercel detects Next.js automatically, we just need to set
`NEXT_PUBLIC_API_BASE_URL` to our deployed Render backend URL as an
environment variable in the Vercel dashboard.
