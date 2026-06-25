# Evaluation (LangSmith dataset + LLM-as-judge)

This phase answers a different question than the rest of the project:
not "does ORACLE run?" but "is ORACLE's output actually _good_, and did
my last prompt change make it better or worse?"

No new accounts needed, this reuses your existing LangSmith key
(`docs/GET_API_KEYS.md` §3) and the `openevals` package
(LangChain's official LLM-as-judge library), which routes its judge calls
through the same OpenRouter free models the rest of the app already uses.

## Running an evaluation

```bash
cd backend
source .venv/bin/activate
python -m eval.run_eval
```

This makes real OpenRouter + Tavily calls, a full run over the 8-query
seed dataset takes roughly **10-20 minutes** and uses a meaningful chunk
of your free-tier quota (each query runs the entire agent graph, so
expect ~10-20 LLM calls and ~5-10 Tavily searches _per query_, similar to
running `run_local.py` eight times). Run it deliberately, after changing
a prompt, swapping a model, or on the weekly CI schedule, not casually.

When it finishes, you'll get a local summary table plus a link to the
full experiment in LangSmith, where every row links straight through to
that example's complete agent trace (every LLM call, every tool call)
so a low score isn't just a number, you can click directly into _why_ a
particular report scored that way.

## What gets measured

Four evaluators run against every report (`backend/eval/evaluators.py`):

| Evaluator                 | Type          | What it catches                                                                                                                                                           |
| ------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `structural_completeness` | deterministic | A broken/malformed report (missing title, no sections, invalid confidence score). Should always score 1.0 — a failure here means a bug, not "could be better."            |
| `citation_integrity`      | deterministic | A section referencing a citation id that doesn't exist in the report's citation list, exactly the bug class a citation-formatter indexing mistake would produce.          |
| `relevance`               | LLM-as-judge  | Does the report actually, substantively answer the query, vs. vague hand-waving that never commits to content?                                                            |
| `synthesis_quality`       | LLM-as-judge  | Does the report read as a genuine synthesis across sources (disagreements surfaced, confidence consistent with tone) vs. several findings just concatenated back-to-back? |

The two deterministic checks are free, instant, and should essentially
never fail, they're guard rails, not quality metrics. The two LLM-judge
scores are where you'll actually see meaningful 0.0–1.0 variation, and
where prompt/model changes will move the needle.

## The dataset

`backend/eval/dataset.json`, 8 queries spanning different domains (tech,
health, economics, science) deliberately chosen so a single domain's
quirks don't dominate the score. Each entry has:

```json
{
  "query": "What are the main approaches to retrieval-augmented generation?",
  "notes": "A good answer should distinguish at least two distinct RAG strategies..."
}
```

`notes` is _not_ a required-match reference answer — research questions
rarely have one canonical answer. It's loose grading guidance fed into the
`relevance` judge's prompt, explicitly framed (in
`eval/evaluators.py`'s `_RELEVANCE_PROMPT`) as "a loose guide, don't
penalize reasonable angles the notes don't mention."

**To add your own eval cases:** just add entries to `dataset.json` and
re-run `eval/run_eval.py` — `get_or_create_dataset()` only seeds a
dataset that doesn't exist yet, so to pick up _new_ entries in an
already-created dataset, either delete the `oracle-report-quality`
dataset in the LangSmith UI first (it'll be recreated with your updated
file on the next run), or add new examples directly via
`client.create_examples(...)` for an existing dataset — see LangSmith's
"manage datasets programmatically" docs if you want to script that
instead of using the UI.

## Reading results

In the LangSmith UI, open your `oracle-report-quality-evals` project (or
whatever `LANGSMITH_PROJECT` you're using) and find the experiment named
`oracle-report-quality-<timestamp>`. You get:

- A table: one row per query, one column per evaluator score
- Click any row to see that specific report alongside its full agent
  trace — useful for understanding _why_ `relevance` scored low (was the
  Supervisor's plan bad? Did a specialist agent's search come up empty?)
- Compare two experiments side-by-side (e.g. before/after a prompt
  change) directly in the UI to see exactly which queries moved and by
  how much

## Customizing the judge

`eval/evaluators.py` routes both LLM-as-judge evaluators through
`build_chat_model()` (the same OpenRouter wrapper everything else uses),
currently pointed at `meta-llama/llama-3.3-70b-instruct:free`. If you want
a stricter or more reliable judge:

- Swap `_JUDGE_MODEL` in `eval/evaluators.py` for a larger free model, or
- Pass a different `judge=` argument to `create_llm_as_judge(...)`, it
  accepts any LangChain chat model instance, so you could point it at a
  paid OpenAI/Anthropic model via their own SDKs if you want a judge
  that's deliberately a different (and presumably stronger) model family
  than whatever generated the report, which is generally good practice
  for LLM-as-judge setups to avoid a model rating its own output family
  favorably.

## Running this in CI

`.github/workflows/eval.yml` runs this on a **weekly schedule** (Mondays)
plus on-demand via the Actions tab's "Run workflow" button, deliberately
**not** on every push, since each run costs real API quota and takes
10-20 minutes. This catches silent regressions (e.g. an OpenRouter free
model getting swapped out from under you) even on weeks with no code
changes. If you want it to also run automatically when someone edits
`app/agents/prompts.py` specifically, add a `paths:` filter under a
`pull_request:` trigger in that workflow file.

For CI, add these five repository secrets (Settings → Secrets and
variables → Actions) alongside the ones from `docs/DEPLOYMENT.md`:
`OPENROUTER_API_KEY`, `OPENROUTER_MODELS`, `TAVILY_API_KEY`,
`LANGSMITH_API_KEY`, `CROSSREF_MAILTO` — the same values you put in your
local `.env`.
