import sys
from pathlib import Path

# `eval/` is a sibling of `app/`, not a package under it, and pytest's
# rootdir-based discovery doesn't add the repo root to sys.path the way a
# proper installed package would, add it explicitly so `from eval...`
# imports resolve the same way `python -m eval.run_eval` does.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.evaluators import citation_integrity, structural_completeness  # noqa: E402


def _valid_report(**overrides) -> dict:
    base = {
        "title": "Test Report",
        "summary": "A summary.",
        "sections": [{"heading": "H", "content": "C", "citation_ids": ["c1"]}],
        "citations": [{"id": "c1", "title": "Source One"}],
        "confidence_score": 0.7,
        "error": None,
    }
    base.update(overrides)
    return base


def test_structural_completeness_passes_for_valid_report():
    result = structural_completeness(_valid_report())
    assert result["score"] == 1.0


def test_structural_completeness_fails_missing_title():
    result = structural_completeness(_valid_report(title=None))
    assert result["score"] == 0.0
    assert "title" in result["comment"]


def test_structural_completeness_fails_no_sections():
    result = structural_completeness(_valid_report(sections=[]))
    assert result["score"] == 0.0


def test_structural_completeness_fails_out_of_range_confidence():
    result = structural_completeness(_valid_report(confidence_score=1.5))
    assert result["score"] == 0.0


def test_structural_completeness_fails_on_target_error():
    result = structural_completeness({"error": "no_report_produced"})
    assert result["score"] == 0.0


def test_citation_integrity_passes_when_all_ids_resolve():
    result = citation_integrity(_valid_report())
    assert result["score"] == 1.0


def test_citation_integrity_fails_on_dangling_reference():
    report = _valid_report(
        sections=[{"heading": "H", "content": "C", "citation_ids": ["c1", "c999"]}],
    )
    result = citation_integrity(report)
    assert result["score"] == 0.0
    assert "c999" in result["comment"]


def test_citation_integrity_passes_with_no_citations_referenced():
    report = _valid_report(
        sections=[{"heading": "H", "content": "C", "citation_ids": []}]
    )
    result = citation_integrity(report)
    assert result["score"] == 1.0
