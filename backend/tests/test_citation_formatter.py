from app.agents.citation_formatter import _compute_confidence
from app.agents.schemas import SourceRef


def _result(confidence: float) -> dict:
    """Build a plain dict matching what specialist agents return (.model_dump())."""
    return {
        "subtask_id": "t1",
        "subtask_type": "web_search",
        "summary": "x",
        "sources": [],
        "confidence": confidence,
        "raw_excerpt": "",
        "error": None,
    }


def _verdict(v: str) -> dict:
    return {"claim": "x", "verdict": v, "explanation": "", "sources": []}


def test_compute_confidence_no_results_is_zero():
    assert _compute_confidence([], []) == 0.0


def test_compute_confidence_no_fact_checks_uses_average_subtask_confidence():
    results = [_result(0.8), _result(0.6)]
    assert _compute_confidence(results, []) == 0.7


def test_compute_confidence_blends_in_fact_check_signal():
    results = [_result(0.9)]
    all_supported = [_verdict("supported")]
    all_contradicted = [_verdict("contradicted")]

    score_supported = _compute_confidence(results, all_supported)
    score_contradicted = _compute_confidence(results, all_contradicted)

    assert score_supported > score_contradicted


def test_compute_confidence_is_clamped_to_unit_interval():
    results = [_result(1.0)]
    verdicts = [_verdict("supported") for _ in range(5)]
    score = _compute_confidence(results, verdicts)
    assert 0.0 <= score <= 1.0


def test_source_ref_dedup_key_prefers_doi():
    ref = SourceRef(url="https://example.com/a", title="A Title", doi="10.1/xyz")
    assert ref.dedup_key() == "10.1/xyz"


def test_source_ref_dedup_key_falls_back_to_url_then_title():
    assert SourceRef(url="https://example.com/a").dedup_key() == "https://example.com/a"
    assert SourceRef(title="Some Title").dedup_key() == "some title"
    assert SourceRef().dedup_key() == ""
