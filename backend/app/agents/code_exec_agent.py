"""Code Execution specialist agent, generates a small Python script for a
data-analysis subtask, runs it in the sandbox, and interprets the output."""

from __future__ import annotations

import logging

from app.agents.prompts import CODE_EXEC_AGENT_SYSTEM, CODE_EXEC_INTERPRET_SYSTEM
from app.agents.schemas import Subtask, SubtaskResult
from app.agents.utils import parse_confidence_suffix, strip_code_fences
from app.core.llm import get_default_llm
from app.tools.code_exec_tool import run_python_code

logger = logging.getLogger("oracle.agents.code_exec")


def code_exec_agent(payload: dict) -> dict:
    subtask = Subtask.model_validate(payload["subtask"])
    llm = get_default_llm(temperature=0.0)

    user = f"Subtask: {subtask.description}\nAdditional context/data: {subtask.input_data or '(none given)'}"
    try:
        raw_code = llm.chat(CODE_EXEC_AGENT_SYSTEM, user)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "code_exec_agent code generation failed for subtask %s: %s", subtask.id, exc
        )
        result = SubtaskResult(
            subtask_id=subtask.id,
            subtask_type=subtask.type,
            summary="Could not generate code for this subtask.",
            confidence=0.0,
            error=str(exc),
        )
        return {"subtask_results": [result.model_dump()]}

    code = strip_code_fences(raw_code)
    exec_result = run_python_code(code)

    if exec_result.blocked_reason:
        result = SubtaskResult(
            subtask_id=subtask.id,
            subtask_type=subtask.type,
            summary=f"Code execution was blocked by the sandbox: {exec_result.blocked_reason}",
            confidence=0.0,
            raw_excerpt=code,
            error="blocked",
        )
        return {"subtask_results": [result.model_dump()]}

    output_block = f"STDOUT:\n{exec_result.stdout}\n\nSTDERR:\n{exec_result.stderr}\n\nExit code: {exec_result.exit_code}"

    try:
        raw_summary = llm.chat(
            CODE_EXEC_INTERPRET_SYSTEM,
            f"Subtask: {subtask.description}\n\n{output_block}",
        )
        summary, confidence = parse_confidence_suffix(raw_summary)
    except Exception as exc:  # noqa: BLE001
        summary, confidence = (
            f"Computation ran but its output could not be interpreted: {exc}",
            0.2,
        )

    if exec_result.timed_out or exec_result.exit_code != 0:
        confidence = min(confidence, 0.3)

    result = SubtaskResult(
        subtask_id=subtask.id,
        subtask_type=subtask.type,
        summary=summary,
        confidence=confidence,
        raw_excerpt=f"```python\n{code}\n```\n\n{output_block}"[:2000],
    )
    return {"subtask_results": [result.model_dump()]}
