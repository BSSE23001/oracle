"""Logging setup shared by the FastAPI app, Celery workers, and local scripts."""

from __future__ import annotations

import logging
import sys

from app.config import settings


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        # Already configured (like by uvicorn itself), we just align the level.
        root.setLevel(settings.log_level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%H:%M:%S"
        )
    )
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # Quiet down noisy third-party loggers unless we're debugging.
    if settings.log_level != "DEBUG":
        for noisy in (
            "httpx",
            "httpcore",
            "urllib3",
            "chromadb",
            "sentence_transformers",
        ):
            logging.getLogger(noisy).setLevel(logging.WARNING)
