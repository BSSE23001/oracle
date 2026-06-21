from app.tools.code_exec_tool import run_python_code


def test_simple_computation_succeeds():
    result = run_python_code("print(2 + 2)")
    assert result.blocked_reason is None
    assert result.exit_code == 0
    assert "4" in result.stdout


def test_denylisted_import_is_blocked():
    result = run_python_code("import os\nprint(os.listdir('.'))")
    assert result.blocked_reason is not None
    assert "os" in result.blocked_reason or "disallowed pattern" in result.blocked_reason


def test_network_import_is_blocked():
    result = run_python_code("import requests\nrequests.get('http://example.com')")
    assert result.blocked_reason is not None


def test_syntax_error_is_reported_not_crashed():
    result = run_python_code("this is not valid python(((")
    assert result.blocked_reason is None  # not denylisted, just bad syntax
    assert result.exit_code != 0
    assert result.stderr  # the interpreter's SyntaxError text


def test_timeout_is_enforced():
    result = run_python_code("import time\ntime.sleep(30)", timeout=1)
    assert result.timed_out is True
