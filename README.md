# ORACLE — Multi-Agent Research Intelligence System

An autonomous research assistant that reads the web, reasons over it
through a team of specialist agents, and writes a structured, cited report,
with a human-in-the-loop checkpoint after planning and full LangSmith
tracing of every agent decision.

**Start here:** [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md)
for the architecture and phase plan, then
[`docs/GET_API_KEYS.md`](docs/GET_API_KEYS.md) to get the three free
keys you need, then [`backend/README.md`](backend/README.md) to run it.

## Quick start

**Agent core only, runs from the terminal:**

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
cp .env.example .env   # fill in OPENROUTER_API_KEY, TAVILY_API_KEY, LANGSMITH_API_KEY
python run_local.py "What are the main approaches to retrieval-augmented generation?"
```

**Full API + Postgres + Celery, via Docker Compose:**

```bash
cp backend/.env.example backend/.env   # same 3 keys as above
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose up -d
# API: http://localhost:8000/docs — see docs/RUNNING_BACKEND.md for a full curl walkthrough
```

**Frontend (requires backend running):**

```bash
cd frontend
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 is the default
npm install
npm run dev
# Open http://localhost:3000
```

**Evaluate report quality (requires local backend setup):**

```bash
cd backend
python -m eval.run_eval   # ~10-20 min, real OpenRouter/Tavily calls — see docs/RUNNING_EVALUATION.md
```
