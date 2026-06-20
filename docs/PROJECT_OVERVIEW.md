# ORACLE — Project Overview & Phase Plan

A multi-agent research system: a Supervisor agent decomposes a query into
subtasks, dispatches them to specialist agents (web search, PDF reading,
code execution, fact-checking) in parallel, synthesizes their findings
into a structured report, runs an automatic fact-check pass over its own
claims, and resolves academic citations, with a human-in-the-loop
checkpoint after planning and full LangSmith tracing throughout.

This is being built in checkpointed phases. Tell Claude "continue" in the
same conversation to pick up the next unbuilt phase.

## Architecture (target end state)

```
                              ┌──────────────────┐
   user query ───────────────▶   Supervisor     │
                              └────────┬─────────┘
                                       │ decomposes into subtasks
                                       ▼
                              ┌──────────────────┐
                              │  Human Review    │◀── user approves/edits plan
                              │  (interrupt())   │     (LangGraph HITL)
                              └────────┬─────────┘
                       ┌───────────────┼───────────────┬───────────────┐
                       ▼               ▼               ▼               ▼
                   Web Search      PDF Reader       Code Exec      Fact Checker
                    (Tavily)       (PyMuPDF +      (sandboxed     (explicit plan
                                   pdfplumber)     subprocess)     claims only)
                       └───────────────┼────────────────┴───────────────┘
                                       ▼
                              ┌──────────────────┐
                              │  Synthesis Agent │
                              └────────┬─────────┘
                                       ▼
                              ┌──────────────────┐
                              │ Fact-Check Pass  │  (re-verifies the draft's
                              │                  │   own key claims)
                              └────────┬─────────┘
                                       ▼
                              ┌──────────────────┐
                              │Citation Formatter│  (CrossRef-resolved
                              └────────┬─────────┘   citations + confidence score)
                                       ▼
                         { title, summary, sections[],
                           citations[], confidence_score }
```

Every box above is traced end-to-end in LangSmith, every LLM call, every
tool call, token counts, and latency, viewable as a single expandable run.

## Why these specific design choices

- **Tool-calling-lite agents, not full ReAct loops.** Free OpenRouter
  models have inconsistent function-calling support. Rather than depend
  on that, each specialist node calls its tool deterministically (the
  subtask already tells it what to search/read/run), then asks the LLM to
  summarize the _result_, much more reliable across 7B-70B free models
  than hoping they invoke tools correctly on their own. See
  `app/core/llm.py` for the structured-JSON workaround this implies for
  the plan/report shapes.
- **Local embeddings by default.** `BAAI/bge-small-en-v1.5` via
  `sentence-transformers` needs no API key and runs offline after the
  first model download, so the whole system needs exactly 2 paid-API-key
  equivalents (OpenRouter, Tavily; both have generous free tiers) plus one
  free observability key (LangSmith) to run end-to-end.
- **Chroma in embedded mode, not a server.** Matches "Chroma DB (local)"
  from the original spec, `chromadb.PersistentClient` just writes to a
  folder on disk, no extra Docker service. If we'd rather run it as a
  proper server (e.g. to share one Chroma instance across multiple
  backend replicas), swap `PersistentClient` for `HttpClient` in
  `app/tools/vector_store.py` and add the `chromadb/chroma` image to
  `docker-compose.yml`, that's a localized, two-line change.
- **Specific agents have graceful fallbacks**, not hard failures: a
  `pdf_reader` subtask with no document URL falls back to a web search; a
  failed LLM call falls back to the next OpenRouter model in the list; a
  failed synthesis call falls back to a raw-findings dump rather than
  crashing the run.

## Repository layout

```
oracle/
├── .github/workflows/              # CI + the two CI-gated deploy workflows
├── backend/
│   ├── app/
│   │   ├── config.py               # Settings, loaded from .env
│   │   ├── core/                   # LLM (OpenRouter+fallback), embeddings, logging
│   │   ├── agents/                 # The graph itself: state, schemas, prompts, nodes
│   │   ├── tools/                  # Tavily, PDF, CrossRef, code-exec, Chroma
│   │   ├── api/                    # FastAPI routes + request/response schemas
│   │   ├── db/                     # SQLAlchemy models, sync+async sessions, CRUD
│   │   ├── tasks/                  # Celery app + the task that drives the graph
│   │   └── services/               # (reserved; empty for now)
│   ├── alembic/                    # DB migrations
│   ├── tests/                      # pytest, pure-logic tests, no live API calls
│   ├── eval/                       # LangSmith dataset + evaluators
│   ├── run_local.py                # CLI test harness
│   ├── requirements.txt
│   ├── ruff.toml
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml              # Postgres + Redis + api + worker (local dev)
├── render.yaml                     # Render Blueprint (production api + worker + redis)
├── frontend/                       # Next.js app
├── docs/                           # You are here
└── README.md
```
