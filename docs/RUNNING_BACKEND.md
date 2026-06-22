# Running FastAPI + Postgres + Celery/Redis

Agent graph in a real API: `POST` a query, get a `session_id` back immediately,
watch the whole run live over Server-Sent Events, approve/edit the plan when
prompted, and fetch the finished report, all without your HTTP client
(or browser) needing to stay blocked waiting on a multi-minute agent run.

No new accounts are needed for this phase, Postgres and Redis both run
locally via Docker Compose.

## 1. Start the infrastructure

```bash
# from the repo root
cp backend/.env.example backend/.env
docker compose up -d postgres redis
```

## 2. Run the database migrations

```bash
docker compose run --rm api alembic upgrade head
```

This creates the four tables (`research_sessions`, `research_reports`,
`agent_events`, `feedback`), see `backend/alembic/versions/0001_initial_schema.py`.

## 3. Start the API and the worker

```bash
docker compose up -d
docker compose logs -f worker
```

The API is now at **http://localhost:8000** (Swagger UI at
`http://localhost:8000/docs`, auto-generated from the FastAPI routes).

## 4. Walk through a full research run via curl

**Start a run:**

```bash
curl -s -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main approaches to retrieval-augmented generation?"}'
```

```json
{ "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", "status": "pending" }
```

**Watch it live** (this streams until the plan-review pause, then again
after you approve, until the report is done, open it in its own
terminal):

```bash
SESSION_ID=3fa85f64-5717-4562-b3fc-2c963f66afa6
curl -N http://localhost:8000/api/research/$SESSION_ID/stream
```

We'll see a stream of SSE events like:

```
event: session_started
id: 1
data: {"node": null, "data": {"query": "What are the main approaches..."}}

event: plan_review_required
id: 2
data: {"node": "human_review", "data": {"plan": {...}, "instructions": "..."}}
```

**Approve the plan** (or send feedback, same endpoint, `approved: false`):

```bash
curl -s -X POST http://localhost:8000/api/research/$SESSION_ID/review \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

The `stream` terminal keeps going from here, `node_update` events for
each specialist agent as it finishes, then `session_completed` with the
full report as its payload.

**Fetch the session/report anytime** (doesn't require the stream to be open):

```bash
curl -s http://localhost:8000/api/research/$SESSION_ID | python3 -m json.tool
```

**Leave feedback on a finished report:**

```bash
curl -s -X POST http://localhost:8000/api/reports/<report_id>/feedback \
  -H "Content-Type: application/json" \
  -d '{"rating": 5, "comment": "Citations were spot-on."}'
```

## How streaming actually works (so debugging makes sense)

- The **Celery worker** is the only thing that ever calls
  `graph.stream(...)`. It iterates LangGraph's `stream_mode="updates"`
  output node-by-node and, for each one, both (a) writes a row to the
  `agent_events` Postgres table and (b) publishes the same event to a
  Redis pub/sub channel named `oracle:events:{session_id}`.
- The **FastAPI SSE endpoint** (`GET /api/research/{id}/stream`)
  subscribes to that Redis channel _and_ replays everything already in
  `agent_events` for that session, in order, before forwarding new live
  messages, so connecting (or reconnecting) at any point during or after
  a run shows the complete history, not just whatever happens to be
  published from that moment on.
- When the supervisor's plan hits the `interrupt()` checkpoint, the
  worker task **returns** (it doesn't block waiting for your decision,
  that would tie up a worker slot for however long a human takes to
  click a button). `POST /review` enqueues a _separate_ Celery task
  (`resume_research_task`) that resumes the same LangGraph thread via
  `Command(resume=...)`.
- `CHECKPOINTER_BACKEND=postgres` in Docker Compose (overriding the
  `sqlite` default in `.env`, which is meant for `run_local.py`
  CLI flow), this is what lets the worker resume a paused plan-review
  days later, or after a worker restart, since the paused state lives
  in Postgres rather than a single worker's local disk.

## Troubleshooting

- **`alembic upgrade head` fails to connect**, make sure
  `docker compose up -d postgres redis` finished and the healthcheck
  passed (`docker compose ps` should show postgres as `healthy`) before
  running migrations.
- **Stream connects but nothing happens**, check
  `docker compose logs worker`; if you see model-fallback warnings, see
  the "free models are rate-limited" note in `backend/README.md`.
- **`session_failed` event with a database error**, the worker and api
  containers both need `CHECKPOINTER_BACKEND=postgres`; if you edited
  `docker-compose.yml` and dropped that override, the worker will try
  (and fail) to open a sqlite file inside its own ephemeral container
  filesystem.
