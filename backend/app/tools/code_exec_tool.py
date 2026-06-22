"""
Code execution tool: runs LLM-generated Python in a subprocess sandbox for
data-analysis subtasks (Like "compute summary statistics on these numbers
pulled from the PDF table").

Threat model: this protects against accidental or sloppy generated code, not
against a determined adversary. It is intended for single-tenant, trusted
research use. If we deploy ORACLE multi-tenant or expose this to untrusted
input, run it inside its own throwaway container (no network, read-only
root fs, dropped capabilities) rather than relying on this in-process
subprocess sandbox alone. Check docs/DEPLOYMENT.md for a hardened option.

Mitigations applied here:
  - runs in a fresh subprocess, never via exec()/eval() in-process
  - `python -I` (isolated mode): ignores PYTHONPATH/PYTHONHOME, no user site
  - CPU time, memory, and process-count rlimits (POSIX only)
  - wall-clock timeout via subprocess.run(timeout=...)
  - static denylist of filesystem/network/process-control imports
  - stdout/stderr size caps to keep prompt context bounded
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger("oracle.tools.code_exec")

_DENYLIST = (
    "import os",
    "from os",
    "import sys",
    "import subprocess",
    "import socket",
    "import shutil",
    "import requests",
    "import urllib",
    "import http",
    "import ctypes",
    "import importlib",
    "__import__",
    "open(",
    "exec(",
    "eval(",
)


@dataclass
class CodeExecResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    truncated: bool
    blocked_reason: str | None = None


def _denylisted_pattern(code: str) -> str | None:
    for pattern in _DENYLIST:
        if pattern in code:
            return pattern
    return None


def _limit_resources() -> None:
    """preexec_fn target: applies rlimits inside the forked child before exec."""
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NPROC, (16, 16))


def run_python_code(code: str, timeout: int | None = None) -> CodeExecResult:
    """
    Execute `code` (a self-contained Python script, it should print()
    whatever it wants the agent to see; there's no notebook-style implicit
    display) and return captured output.
    """
    timeout = timeout or settings.code_exec_timeout_seconds

    blocked = _denylisted_pattern(code)
    if blocked:
        return CodeExecResult(
            stdout="",
            stderr="",
            exit_code=-1,
            timed_out=False,
            truncated=False,
            blocked_reason=(
                f"Code contains disallowed pattern '{blocked}'. This sandbox only "
                "permits pure computation (pandas, numpy, math, statistics, json, "
                "re, collections, itertools, datetime) — no filesystem, process, "
                "or network access."
            ),
        )

    fd, script_path = tempfile.mkstemp(suffix=".py")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(code)

        run_kwargs: dict = {}
        if os.name == "posix":
            run_kwargs["preexec_fn"] = _limit_resources

        proc = subprocess.run(
            [sys.executable, "-I", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            **run_kwargs,
        )

        stdout, stderr, truncated = proc.stdout, proc.stderr, False
        max_chars = settings.code_exec_max_output_chars
        if len(stdout) > max_chars:
            stdout, truncated = stdout[:max_chars], True
        if len(stderr) > max_chars:
            stderr, truncated = stderr[:max_chars], True

        return CodeExecResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=proc.returncode,
            timed_out=False,
            truncated=truncated,
        )
    except subprocess.TimeoutExpired:
        return CodeExecResult(
            stdout="",
            stderr=f"Execution timed out after {timeout}s",
            exit_code=-1,
            timed_out=True,
            truncated=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Code execution failed unexpectedly: %s", exc)
        return CodeExecResult(
            stdout="", stderr=str(exc), exit_code=-1, timed_out=False, truncated=False
        )
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
