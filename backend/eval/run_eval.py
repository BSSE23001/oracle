"""
Run ORACLE's report-quality evaluation against the LangSmith dataset
defined in `eval/dataset.json`.

Usage:
    cd backend
    source .venv/bin/activate
    python -m eval.run_eval

What this does:
  1. Connects to LangSmith and creates the `oracle-report-quality` dataset
     from `eval/dataset.json` if it doesn't exist yet (idempotent, safe
     to run repeatedly, it won't duplicate examples on subsequent runs).
  2. Runs the full ORACLE agent graph (`eval/target.py`) against every
     example query, auto-approving the human-in-the-loop plan review.
  3. Scores each resulting report with the four evaluators in
     `eval/evaluators.py` (2 deterministic, 2 LLM-as-judge).
  4. Prints a summary table and a link to the full experiment in
     LangSmith, where you can drill into any individual run's full agent
     trace alongside its scores.

Cost/time note: this makes real OpenRouter + Tavily calls, a full run
over the default 8-query dataset takes roughly 10-20 minutes and costs
nothing against free-tier quotas, but DOES consume a meaningful chunk of
your daily OpenRouter/Tavily free-tier allowance (~10-20 LLM calls and
~5-10 Tavily searches per query, see backend/README.md's rate-limit
notes). `max_concurrency` below is intentionally conservative (2) to
avoid bursting through OpenRouter's free-tier rate limit across multiple
queries running at once.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from langsmith import Client, evaluate

from app.config import configure_langsmith_env, settings
from app.core.logging_config import configure_logging
from eval.evaluators import ALL_EVALUATORS
from eval.target import run_oracle_target

logger = logging.getLogger("oracle.eval.run")

DATASET_NAME = "oracle-report-quality"
DATASET_PATH = Path(__file__).parent / "dataset.json"
EXPERIMENT_PREFIX = "oracle-report-quality"
MAX_CONCURRENCY = 2


def get_or_create_dataset(client: Client):
    try:
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        logger.info("Using existing dataset %r (id=%s)", DATASET_NAME, dataset.id)
        return dataset
    except (
        Exception
    ):  # noqa: BLE001 - LangSmith raises on "not found"; any failure here means "create it"
        logger.info(
            "Dataset %r not found — creating it from %s", DATASET_NAME, DATASET_PATH
        )

    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Representative research queries for evaluating ORACLE end-to-end report quality.",
    )
    seed_examples = json.loads(DATASET_PATH.read_text())
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {
                "inputs": {"query": item["query"]},
                "outputs": {"notes": item.get("notes", "")},
            }
            for item in seed_examples
        ],
    )
    logger.info("Seeded %d examples into %r", len(seed_examples), DATASET_NAME)
    return dataset


def main() -> None:
    configure_logging()
    configure_langsmith_env()

    if not settings.langsmith_tracing or not settings.langsmith_api_key:
        raise SystemExit(
            "LANGSMITH_TRACING=true and LANGSMITH_API_KEY must be set to run evaluations "
            "(see docs/01_GET_API_KEYS.md section 3). Evaluation results live in LangSmith, "
            "so there's no meaningful way to run this without it."
        )

    client = Client()
    get_or_create_dataset(client)

    logger.info(
        "Starting evaluation run — this makes real OpenRouter/Tavily calls, expect ~10-20 minutes."
    )
    results = evaluate(
        run_oracle_target,
        data=DATASET_NAME,
        evaluators=ALL_EVALUATORS,
        experiment_prefix=EXPERIMENT_PREFIX,
        max_concurrency=MAX_CONCURRENCY,
        metadata={"oracle_phase": "5"},
    )

    rows = list(results)

    print("\n" + "=" * 78)
    print(f"Evaluation complete — {len(rows)} examples.")
    print("View full agent traces alongside scores for every run at:")
    print("  https://smith.langchain.com")
    print(
        f"  (project: {settings.langsmith_project}, experiment prefix: {EXPERIMENT_PREFIX})"
    )
    print("=" * 78 + "\n")

    for row in rows:
        run = row.get("run")
        example = row.get("example")
        query = (example.inputs.get("query", "?") if example else "?")[:60]
        eval_results = (row.get("evaluation_results") or {}).get("results") or []
        score_str = ", ".join(
            f"{r.key}={r.score:.2f}"
            for r in eval_results
            if getattr(r, "score", None) is not None
        )
        errored = bool(getattr(run, "error", None)) if run is not None else False
        status = "ERROR" if errored else "ok   "
        print(f"  [{status}] {query:<60} {score_str}")


if __name__ == "__main__":
    main()
