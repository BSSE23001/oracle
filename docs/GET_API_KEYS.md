# Getting your API keys

We need three free accounts to run ORACLE's agent core locally. None of
these require a credit card.

Once we have all three values, copy `backend/.env.example` to
`backend/.env` and paste them in. Everything else in `.env.example` has a
working default for local development.

---

## 1. OpenRouter (the LLM)

OpenRouter gives us one API key that can call dozens of models, including
several genuinely free ones (no spend, just rate-limited).

1. Go to **https://openrouter.ai** and sign up (Google/GitHub/email).
2. Click profile icon → **Keys** (or go directly to
   **https://openrouter.ai/keys**).
3. Click **Create Key**, give it a name like `oracle-dev`, and copy the
   value, it looks like `sk-or-v1-...`. We will not be able to see it
   again after we navigate away, so paste it into `backend/.env` as
   `OPENROUTER_API_KEY` right away.
4. Free models change over time as providers rotate what they offer for
   free. Check **https://openrouter.ai/models?max_price=0** for the
   current list and update `OPENROUTER_MODELS` in `.env` if the ones we
   shipped with (`llama-3.3-70b-instruct:free`, `qwen-2.5-72b-instruct:free`,
   `mistral-7b-instruct:free`) have been retired. ORACLE tries them in
   order and automatically falls back to the next one if a model is
   rate-limited or errors, so listing 2-3 is a good idea.
5. Free-tier rate limits are roughly 20 requests/minute and 50-200
   requests/day depending on account age and whether we've ever added
   credits, see **https://openrouter.ai/docs/api-reference/limits**. A
   single ORACLE research run makes somewhere between 8 and 20 LLM calls
   (one per subtask, plus synthesis, plus up to 5 fact-check calls), so
   we'll be able to run a handful of research sessions per day on the
   free tier alone.

## 2. Tavily (web search)

1. Go to **https://www.tavily.com** and sign up.
2. After signing in we land on a dashboard showing our API key directly
   (starts with `tvly-`) — no extra navigation needed.
3. Copy it into `backend/.env` as `TAVILY_API_KEY`.
4. The free tier includes **1,000 searches/month**, which is generous for
   development. Each ORACLE research run uses roughly 1 search per
   web_search subtask plus up to 5 more during the fact-check pass, so
   call it 5-10 searches per run.

## 3. LangSmith (observability)

(optional for the agents to function)

LangSmith is what makes the multi-agent traces visible, clicking into a
run shows every LLM call, every tool call, token counts, and latency,
which is the single most impressive thing to show off in a demo. The
agents will still work with tracing turned off (`LANGSMITH_TRACING=false`)
if you'd rather skip this for now.

1. Go to **https://smith.langchain.com** and sign up.
2. You'll be dropped into a default workspace. Go to **Settings** (gear
   icon, bottom left) → **API Keys** → **Create API Key**.
3. Copy the key (starts with `lsv2_`) into `backend/.env` as
   `LANGSMITH_API_KEY`, and set `LANGSMITH_TRACING=true`.
4. `LANGSMITH_PROJECT` in `.env.example` is set to
   `oracle-research-assistant`, LangSmith creates that project
   automatically the first time a trace comes in, we don't need to
   pre-create it.
5. The free tier ("Developer" plan) includes 5,000 traces/month, far more
   than we'll use in development. See
   **https://www.langchain.com/pricing-langsmith** for current limits.
6. After running `python run_local.py "some query"` once, go to
   **https://smith.langchain.com**, open the `oracle-research-assistant`
   project, and click into the run, we'll see the full
   supervisor → human-review → parallel-agents → synthesis →
   fact-check → citation tree, with every prompt/response pair.

---

## Things we do NOT need an API key for

- **Embeddings** — the default `EMBEDDING_PROVIDER=huggingface` runs
  `BAAI/bge-small-en-v1.5` locally via `sentence-transformers`. The first
  run downloads ~130MB of model weights from Hugging Face's public CDN
  (no account needed) and caches them under `~/.cache/huggingface/`.
  Every run after that is fully offline.
- **CrossRef** (citation metadata) is a free, keyless API. Setting
  `CROSSREF_MAILTO` in `.env` to your own email is optional but gets us
  into their faster "polite pool", see
  **https://api.crossref.org/swagger-ui/index.html**.
- **Chroma** (vector store) runs as an embedded local database, just a
  folder on disk (`./data/chroma` by default), no service or account.

## Used at the time of Deployment

- **Supabase** (Postgres) and **Redis**, needed once the
  FastAPI + Celery layer is added. A setup guide for these will
  be added in Deployment Guide.
- **Render** and **Vercel**, needed for the CI/CD deployment phase. A
  setup guide for these will be added then.

---

## Verifying everything works

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env                # then paste in keys
python run_local.py "What are the main approaches to retrieval-augmented generation?"
```

We should see: a plan table printed to the terminal, a yes/no prompt to
approve it, then live log lines as the specialist agents run, and finally
a formatted report with a confidence score and a citation list. If
`LANGSMITH_TRACING=true`, a link to the full trace prints at the end.
