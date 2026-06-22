"""
Evaluators for ORACLE report quality.

Two kinds, deliberately combined:

- **Deterministic / programmatic** (`structural_completeness`,
  `citation_integrity`), free, instant, zero false-positive-rate guard
  rails that catch outright bugs (a malformed report, a citation id a
  section references that doesn't actually exist in the citations list).
  These should basically always score 1.0; if they don't, something in
  the pipeline broke, not just "the report could be better."

- **LLM-as-judge** (`relevance_judge`, `synthesis_quality_judge`), built
  with `openevals.llm.create_llm_as_judge`, judging genuinely subjective
  qualities a programmatic check can't: does the report actually answer
  the question, and is it a real synthesis rather than a concatenated
  dump of findings. Both are routed through `build_chat_model()` from
  `app/core/llm.py`, i.e. the same OpenRouter free-tier models the rest
  of the app uses, so running evals needs no extra API key beyond what
  Phase 1 already requires. Note this means importing this module
  requires OPENROUTER_API_KEY to already be set (same as running the
  graph itself does), there's no point deferring that here, since
  `eval/run_eval.py` is going to need a working OpenRouter connection
  regardless to run the target function.

Every evaluator here uses the modern kwargs-based signature LangSmith's
`evaluate()` introspects by parameter name (`inputs`, `outputs`,
`reference_outputs`), see https://docs.smith.langchain.com (How to define
a code evaluator) for the current convention this matches.
"""

from __future__ import annotations

from openevals.llm import create_llm_as_judge

from app.core.llm import build_chat_model

# A mid-size free model is a reasonable judge, strong enough to follow a
# rubric, while keeping eval runs on the same free tier as everything
# else. We can swap this for a larger model (or a paid one) if we want a
# stricter/more reliable judge.
_JUDGE_MODEL = "meta-llama/llama-3.3-70b-instruct:free"


# ── Deterministic evaluators ─────────────────────────────────────────────


def structural_completeness(outputs: dict) -> dict:
    """A valid report must have a title, a summary, at least one section,
    and a confidence score in [0, 1]. This should never legitimately fail,
    a failure here means the graph produced a broken report, not a
    low-quality one."""
    if outputs.get("error"):
        return {
            "key": "structural_completeness",
            "score": 0.0,
            "comment": f"target errored: {outputs['error']}",
        }

    has_title = bool(outputs.get("title"))
    has_summary = bool(outputs.get("summary"))
    has_sections = len(outputs.get("sections") or []) >= 1
    score_field = outputs.get("confidence_score")
    has_valid_confidence = (
        isinstance(score_field, (int, float)) and 0.0 <= score_field <= 1.0
    )

    ok = has_title and has_summary and has_sections and has_valid_confidence
    missing = [
        name
        for name, present in [
            ("title", has_title),
            ("summary", has_summary),
            ("sections", has_sections),
            ("valid confidence_score", has_valid_confidence),
        ]
        if not present
    ]
    comment = (
        "all required fields present"
        if ok
        else f"missing/invalid: {', '.join(missing)}"
    )
    return {
        "key": "structural_completeness",
        "score": 1.0 if ok else 0.0,
        "comment": comment,
    }


def citation_integrity(outputs: dict) -> dict:
    """Every citation id a section references must actually exist in the
    report's top-level citations list, this is exactly the class of bug
    a citation-formatter dedup/indexing mistake would produce, and it's
    cheap to catch deterministically rather than relying on a judge to
    happen to notice a dangling reference."""
    if outputs.get("error"):
        return {
            "key": "citation_integrity",
            "score": 0.0,
            "comment": f"target errored: {outputs['error']}",
        }

    citation_ids = {c["id"] for c in (outputs.get("citations") or [])}
    referenced: set[str] = set()
    for section in outputs.get("sections") or []:
        referenced.update(section.get("citation_ids") or [])

    dangling = referenced - citation_ids
    score = 1.0 if not dangling else 0.0
    comment = (
        "all referenced citation ids resolve"
        if not dangling
        else f"dangling citation ids: {sorted(dangling)}"
    )
    return {"key": "citation_integrity", "score": score, "comment": comment}


# ── LLM-as-judge evaluators ─────────────────────────────────────────────

_RELEVANCE_PROMPT = """You are grading whether a research report actually answers the user's query.

<query>
{inputs}
</query>

<report>
{outputs}
</report>

<grading_notes optional="true">
{reference_outputs}
</grading_notes>

Score from 0.0 to 1.0 how directly and thoroughly the report answers the query:
- 1.0: directly and substantively answers the query, covering the key angles a knowledgeable
  person would expect (use the grading notes above as a loose guide to what those angles are,
  if provided — but don't penalize the report for reasonable angles the notes don't mention).
- 0.5: partially answers the query, or answers it but misses an important angle.
- 0.0: does not meaningfully address the query, or is mostly generic filler.

Penalize vague hand-waving ("there are many factors to consider...") that never commits to
substantive content. Do not penalize appropriate hedging about uncertain or contested claims —
that's good epistemic practice, not vagueness.
"""

_SYNTHESIS_QUALITY_PROMPT = """You are grading the synthesis quality of a multi-agent research report.
Several specialist agents researched different angles of a query in parallel; a synthesis agent
then had to combine their findings into one coherent report.

<report>
{outputs}
</report>

Score from 0.0 to 1.0 how well-synthesized the report is:
- 1.0: the sections read as a genuine synthesis — ideas connect across sections, any
  disagreement between underlying sources is surfaced rather than smoothed over, and the
  confidence score is consistent with how hedged or definitive the prose actually reads.
- 0.5: readable but feels more like several findings concatenated back-to-back than truly
  synthesized; minor inconsistency between stated confidence and the report's actual tone.
- 0.0: disorganized, repetitive across sections, or the confidence score clearly contradicts
  the report's content (e.g. high confidence on hedgy, uncertain-sounding prose, or vice versa).
"""

relevance_judge = create_llm_as_judge(
    prompt=_RELEVANCE_PROMPT,
    judge=build_chat_model(_JUDGE_MODEL, temperature=0.0),
    feedback_key="relevance",
    continuous=True,
)

synthesis_quality_judge = create_llm_as_judge(
    prompt=_SYNTHESIS_QUALITY_PROMPT,
    judge=build_chat_model(_JUDGE_MODEL, temperature=0.0),
    feedback_key="synthesis_quality",
    continuous=True,
)

ALL_EVALUATORS = [
    structural_completeness,
    citation_integrity,
    relevance_judge,
    synthesis_quality_judge,
]
