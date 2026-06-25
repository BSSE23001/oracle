"""Small parsing helpers shared by more than one agent node."""

from __future__ import annotations

import re

_CONFIDENCE_RE = re.compile(r"CONFIDENCE:\s*([0-9]*\.?[0-9]+)", re.IGNORECASE)


def coerce_to_dict(obj) -> dict:
    """Convert a Pydantic model instance OR plain dict to a plain dict.

    Used throughout agent nodes so they work correctly with BOTH:
      - new code: nodes return `.model_dump()` plain dicts
      - old checkpoints: LangGraph deserialised stored Pydantic instances back
        from msgpack and those come out as actual model objects rather than dicts.

    Placing this coercion at every READ site (not just every WRITE site) means
    the system degrades gracefully during rolling updates instead of crashing.
    """
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    try:
        return dict(obj)
    except Exception as exc:
        raise TypeError(f"Cannot coerce {type(obj).__name__!r} to dict") from exc


def parse_confidence_suffix(text: str, default: float = 0.5) -> tuple[str, float]:
    """
    Agent prompts ask the model to end its answer with a line like
    `CONFIDENCE: 0.8`. This strips that line off and returns
    (summary_without_confidence_line, confidence_float).
    """
    match = _CONFIDENCE_RE.search(text)
    if not match:
        return text.strip(), default
    try:
        confidence = max(0.0, min(1.0, float(match.group(1))))
    except ValueError:
        confidence = default
    summary = text[: match.start()].strip()
    return summary or text.strip(), confidence


def strip_code_fences(text: str) -> str:
    """Strip a single leading/trailing ``` or ```python fence if present."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
