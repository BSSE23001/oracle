"""
LLM access layer: OpenRouter, with automatic fallback across free models
and a robust "ask for JSON, parse, repair-on-failure" structured output
helper.

Free OpenRouter models have inconsistent function-calling support.
Rather than depend on that, every structured call here asks the
model to emit raw JSON matching a Pydantic schema, extracts the
JSON defensively (handles markdown fences, stray prose, trailing
commas), validates it, and on failure feeds the parse error back
to the model for one repair attempt before moving to the next model in
the fallback chain. This is slower than native tool-calling but works
uniformly across every free-tier model OpenRouter offers.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Type, TypeVar

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.config import settings

logger = logging.getLogger("oracle.llm")

T = TypeVar("T", bound=BaseModel)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


class AllModelsFailedError(RuntimeError):
    """Raised when every model in the fallback chain failed for a request."""


def build_chat_model(model_name: str, temperature: float = 0.2) -> ChatOpenAI:
    """
    A single OpenRouter-backed chat model. OpenRouter speaks the OpenAI
    Chat Completions wire format, so `langchain_openai.ChatOpenAI` works
    unmodified, we just point `base_url` at OpenRouter and pass our
    OpenRouter key as the `api_key`.
    """
    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy backend/.env.example to "
            "backend/.env and fill it in using docs/GET_API_KEYS.md."
        )
    return ChatOpenAI(
        model=model_name,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=temperature,
        timeout=settings.agent_llm_timeout_seconds,
        max_retries=0,  # we handle retries/fallback ourselves, across models
        default_headers={
            "HTTP-Referer": settings.openrouter_site_url,
            "X-Title": settings.openrouter_site_name,
        },
    )


@retry(
    stop=stop_after_attempt(2),
    wait=wait_random_exponential(multiplier=1, max=8),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True,
)
def _invoke_once(
    model_name: str, messages: list[BaseMessage], temperature: float
) -> AIMessage:
    llm = build_chat_model(model_name, temperature)
    return llm.invoke(messages)


class FallbackLLM:
    """
    Wraps a prioritised list of OpenRouter model slugs. Every public method
    walks the list in order and moves on to the next model if the current
    one errors, rate-limits, or returns empty content, so a single
    over-quota free model never takes the whole research run down.
    """

    def __init__(self, models: list[str] | None = None, temperature: float = 0.2):
        self.models = models or settings.openrouter_model_list
        self.temperature = temperature
        if not self.models:
            raise RuntimeError(
                "No OpenRouter models configured (OPENROUTER_MODELS is empty)."
            )

    # ── Plain chat ───────────────────────────────────────────────────────
    def chat(self, system: str, user: str) -> str:
        """Single-turn chat call. Returns the response text."""
        messages: list[BaseMessage] = [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ]
        last_exc: Exception | None = None
        for model_name in self.models:
            try:
                response = _invoke_once(model_name, messages, self.temperature)
                text = (
                    (response.content or "").strip()
                    if isinstance(response.content, str)
                    else str(response.content)
                )
                if text:
                    return text
                logger.warning(
                    "Model %s returned empty content, trying next model.", model_name
                )
            except (
                Exception
            ) as exc:  # noqa: BLE001 - intentionally broad, this is the fallback boundary
                last_exc = exc
                logger.warning(
                    "Model %s failed (%s), trying next model.", model_name, exc
                )
                continue
        raise AllModelsFailedError(
            f"All OpenRouter models failed. Last error: {last_exc}"
        )

    # ── Structured JSON output ──────────────────────────────────────────
    def generate_structured(
        self,
        system: str,
        user: str,
        schema: Type[T],
        max_repair_attempts: int = 1,
    ) -> T:
        """
        Ask for JSON matching `schema`, validate it, and return an instance
        of `schema`. On a parse/validation failure, sends one repair prompt
        back to the same model before giving up on that model and moving
        to the next one in the fallback chain.
        """
        schema_hint = _schema_hint(schema)
        full_system = (
            f"{system}\n\n"
            "You must respond with ONLY a single valid JSON object — no prose, "
            "no markdown code fences, no explanation before or after it. "
            f"The JSON object must match this shape:\n{schema_hint}"
        )
        last_exc: Exception | None = None

        for model_name in self.models:
            messages: list[BaseMessage] = [
                SystemMessage(content=full_system),
                HumanMessage(content=user),
            ]
            attempts_left = max_repair_attempts + 1
            while attempts_left > 0:
                attempts_left -= 1
                try:
                    response = _invoke_once(model_name, messages, self.temperature)
                    raw_text = (
                        response.content
                        if isinstance(response.content, str)
                        else str(response.content)
                    )
                    data = _extract_json(raw_text)
                    return schema.model_validate(data)
                except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                    last_exc = exc
                    if attempts_left > 0:
                        logger.info(
                            "Repairing malformed JSON from %s: %s", model_name, exc
                        )
                        messages.append(
                            AIMessage(
                                content=raw_text if "raw_text" in locals() else ""
                            )
                        )
                        messages.append(
                            HumanMessage(
                                content=(
                                    "That response was not valid JSON matching the required shape. "
                                    f"Validation error: {exc}\n"
                                    "Reply again with ONLY the corrected JSON object."
                                )
                            )
                        )
                    else:
                        logger.warning(
                            "Model %s could not produce valid JSON after retries (%s).",
                            model_name,
                            exc,
                        )
                except (
                    Exception
                ) as exc:  # noqa: BLE001 - network/API errors, move to next model immediately
                    last_exc = exc
                    logger.warning(
                        "Model %s failed (%s), trying next model.", model_name, exc
                    )
                    break
        raise AllModelsFailedError(
            f"All OpenRouter models failed to produce valid JSON. Last error: {last_exc}"
        )


def _schema_hint(schema: Type[BaseModel]) -> str:
    """A compact, human-readable field listing instead of a raw JSON-Schema
    dump, free models follow short examples far more reliably than a
    full JSON-Schema document with defs and refs."""
    lines = []
    for name, field in schema.model_fields.items():
        type_name = getattr(field.annotation, "__name__", str(field.annotation))
        desc = f" — {field.description}" if field.description else ""
        lines.append(f'  "{name}": <{type_name}>{desc}')
    return "{\n" + ",\n".join(lines) + "\n}"


def _extract_json(text: str) -> dict:
    """Defensively pull a JSON object out of an LLM response that may
    contain markdown fences, leading/trailing prose, or trailing commas."""
    text = text.strip()
    fence_match = _JSON_FENCE_RE.search(text)
    candidate = fence_match.group(1).strip() if fence_match else text

    # If there's still leading/trailing prose, grab the outermost {...}
    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]

    # Common small repairs: trailing commas before } or ]
    candidate = re.sub(r",\s*([}\]])", r"\1", candidate)

    return json.loads(candidate)


def get_default_llm(temperature: float = 0.2) -> FallbackLLM:
    return FallbackLLM(temperature=temperature)
