# ORACLE backend

> ## **Celery** is not working correctly with local **Windows** Setup
>
> So to run locally use linux environment, or the best DOCKER.

> **Want to measure report quality, not just run it?**
> `python -m eval.run_eval` scores output against a LangSmith
> dataset using both deterministic checks and LLM-as-judge.

## Setup

Requires Python 3.12 (3.10/3.11/3.13 also work).

> **Running the full API + Postgres + Celery stack instead of just the
> CLI?** it's all driven by Docker Compose (`docker compose up`)
> and doesn't need anything below beyond the same `.env` you set up here.

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Then fill in `.env`, see **`../docs/GET_API_KEYS.md`** for exactly
where to get each value (OpenRouter, Tavily, LangSmith; ~10 minutes).

## Run a research session from the terminal

`run_local.py` drives the agent graph directly, no API server needed,
handy for quick iteration on prompts/agents without going through Docker
Compose:

```bash
python run_local.py "What are the main approaches to retrieval-augmented generation?"
```

This will:

1. Run the Supervisor agent to decompose your query into subtasks.
2. Pause (LangGraph's `interrupt()`) and print the plan as a table.
3. Ask you to approve it or give feedback, feedback sends it back to the
   Supervisor for revision and shows you the new plan; approving moves on.
4. Dispatch the specialist agents for each subtask **in parallel**.
5. Synthesize their findings into a draft report.
6. Run an automatic fact-check pass over the draft's own key claims.
7. Resolve citations via CrossRef and print the final report with a
   confidence score.

If `LANGSMITH_TRACING=true` in our `.env`, a link to the full trace
prints at the end, open it to see literally every LLM call and tool call
any agent made, in order, with latencies and token counts.

## Project layout

```
app/
├── config.py                 # Settings, everything is read from .env via this
├── core/
│   ├── llm.py                # OpenRouter chat model + automatic model fallback
│   │                           + the "ask for JSON, validate, repair-on-failure"
│   │                           structured-output helper (no reliance on native
│   │                           tool-calling, which free models support inconsistently)
│   ├── embeddings.py         # Local HuggingFace embeddings (default) or OpenAI
│   └── logging_config.py
├── agents/
│   ├── state.py              # The LangGraph state TypedDict (with fan-out reducers)
│   ├── schemas.py            # Pydantic models: Plan, Subtask, Citation, Report, ...
│   ├── prompts.py            # Every system prompt, in one place
│   ├── supervisor.py         # Decomposes the query; revises on feedback
│   ├── human_review.py       # The interrupt() human-in-the-loop checkpoint
│   ├── web_search_agent.py   # Tavily search + summarize
│   ├── pdf_agent.py          # PyMuPDF/pdfplumber read + summarize
│   ├── code_exec_agent.py    # Generate + sandboxed-run + interpret Python
│   ├── fact_check_subtask_agent.py  # Explicit "verify this claim" subtasks
│   ├── fact_check_logic.py   # Shared claim-verification helper (search + LLM judge)
│   ├── fact_check_pass.py    # Auto re-checks the synthesized report's own claims
│   ├── synthesis_agent.py    # Fan-in: combines all findings into a draft report
│   ├── citation_formatter.py # Resolves CrossRef metadata; computes confidence_score
│   └── graph.py              # Wires every node above into the StateGraph
└── tools/
    ├── web_search_tool.py    # Tavily client
    ├── pdf_tools.py          # PyMuPDF (fast text) + pdfplumber (tables)
    ├── crossref_tool.py      # Free keyless citation metadata API
    ├── code_exec_tool.py     # Subprocess sandbox: rlimits, timeout, denylist
    └── vector_store.py       # Local Chroma: chunk, embed, ingest, retrieve

api/
├── schemas.py                # Request/response Pydantic models
├── routes_research.py        # POST/GET /api/research, plan review, SSE stream
└── routes_reports.py         # GET /api/reports, POST .../feedback

db/
├── models.py                 # SQLAlchemy 2.0 models: sessions, reports, events, feedback
├── session.py                # Async engine (FastAPI) + sync engine (Celery)
└── crud.py                   # Async CRUD (routes) + _sync CRUD (Celery tasks)

tasks/
├── celery_app.py             # Celery configuration
└── research_tasks.py         # The task that calls graph.stream() and publishes events

eval/
├── dataset.json              # Seed queries for the LangSmith evaluation dataset
├── target.py                 # Runs the full graph end-to-end, auto-approving plan review
├── evaluators.py             # 2 deterministic + 2 LLM-as-judge evaluators
└── run_eval.py               # Entry point: `python -m eval.run_eval`

main.py                       # FastAPI app, CORS, router registration, /health
```

## Notes on things that are easy to get wrong here

- **The graph requires a checkpointer.** `interrupt()` only works with one
  attached. `build_graph()` defaults to a local SQLite file
  (`./data/checkpoints.sqlite`), which is what `run_local.py` uses, fine
  for single-process CLI testing. The Docker Compose stack sets
  `CHECKPOINTER_BACKEND=postgres` instead, since the FastAPI process and
  the Celery worker process are separate and a paused plan-review needs
  to be resumable by the worker regardless of which container (or restart)
  picks up the resume task.
- **`thread_id` is the resume key.** Every `graph.invoke()`/`.stream()`
  call needs `config={"configurable": {"thread_id": session_id}}`, that's
  what LangGraph uses to find the paused checkpoint to resume from.
  `run_local.py` generates one random UUID per run; the API uses
  the actual `research_sessions.id` from Postgres as the thread id, so
  `GET /api/research/{id}` and the LangGraph thread always agree.
- **Free OpenRouter models are rate-limited and occasionally flaky.**
  That's exactly what `FallbackLLM` in `core/llm.py` exists for, if we
  see log lines like `Model X failed (...), trying next model`, that's
  the fallback working as intended, not a bug. If _all_ models in
  `OPENROUTER_MODELS` fail, check that the slugs are still offered for
  free at https://openrouter.ai/models?max_price=0 (these rotate) and
  update the `.env`.
- **The code-exec sandbox is for trusted single-user use.** It runs
  LLM-generated Python in a subprocess with rlimits/timeout/an import
  denylist, which protects against sloppy generated code, not a
  determined adversary. See the docstring at the top of
  `app/tools/code_exec_tool.py` if you're deploying this multi-tenant.
