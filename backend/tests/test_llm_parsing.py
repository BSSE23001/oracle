from app.core.llm import _extract_json
from app.agents.utils import parse_confidence_suffix, strip_code_fences


def test_extract_json_plain():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_markdown_fence():
    text = '```json\n{"a": 1, "b": "two"}\n```'
    assert _extract_json(text) == {"a": 1, "b": "two"}


def test_extract_json_with_surrounding_prose():
    text = 'Sure, here is the JSON:\n{"a": 1}\nLet me know if you need anything else!'
    assert _extract_json(text) == {"a": 1}


def test_extract_json_with_trailing_comma():
    text = '{"a": 1, "b": 2,}'
    assert _extract_json(text) == {"a": 1, "b": 2}


def test_parse_confidence_suffix_present():
    text = "This is the summary.\nCONFIDENCE: 0.85"
    summary, confidence = parse_confidence_suffix(text)
    assert summary == "This is the summary."
    assert confidence == 0.85


def test_parse_confidence_suffix_missing_uses_default():
    text = "This is the summary with no confidence line."
    summary, confidence = parse_confidence_suffix(text, default=0.5)
    assert summary == text
    assert confidence == 0.5


def test_parse_confidence_suffix_clamps_out_of_range():
    text = "Summary.\nCONFIDENCE: 1.7"
    _, confidence = parse_confidence_suffix(text)
    assert confidence == 1.0


def test_strip_code_fences_with_language_tag():
    text = "```python\nprint('hi')\n```"
    assert strip_code_fences(text) == "print('hi')"


def test_strip_code_fences_no_fence():
    text = "print('hi')"
    assert strip_code_fences(text) == "print('hi')"
