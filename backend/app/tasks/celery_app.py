"""
Celery application. Research runs are dispatched here rather than run
inline in a FastAPI request handler because a full run is many sequential
LLM calls deep (plan -> N parallel specialists -> synthesis -> up to 5
fact-checks -> citations) and can take anywhere from 30 seconds to a few
minutes — long enough that you don't want it tying up a web worker's
event loop, and long enough that it should survive a web server restart
(the Celery worker is a separate process).

Worker startup hooks
--------------------
`worker_process_init` fires once inside each freshly forked worker process.
We use it to:

1. Call `configure_langsmith_env()` — LangSmith reads tracing config from
   environment variables at import/call time.  The env vars must be set in
   the *worker* process; setting them in the FastAPI process has no effect
   on the separately-forked worker processes.
2. Call `configure_logging()` — so each worker process applies our standard
   log format from the very first log line rather than defaulting to the
   root logger's format.
"""

from __future__ import annotations

from celery import Celery
from celery.signals import worker_process_init

from app.config import configure_langsmith_env, settings
from app.core.logging_config import configure_logging

celery_app = Celery(
    "oracle",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.research_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # A full research run should never legitimately run longer than this.
    # The previous 900/840-second limits were too tight: sequential CrossRef
    # calls and sequential fact-checking alone could consume ~5 minutes.
    # Both are now parallelised (see citation_formatter.py, fact_check_pass.py),
    # but we keep generous headroom for edge cases (slow OpenRouter responses,
    # many subtasks, large PDF reads, etc.).
    task_time_limit=1200,        # hard kill after 20 minutes
    task_soft_time_limit=1080,   # SoftTimeLimitExceeded at 18 minutes
    worker_max_tasks_per_child=50,  # periodically recycle workers (embeddings model memory, etc.)
)


@worker_process_init.connect
def _on_worker_process_init(**kwargs) -> None:  # noqa: ANN003
    """Called once inside every freshly forked Celery worker process.

    Must be done here — not in the parent process — because forked children
    do NOT inherit Python-level state set after `celery worker` has started
    (environment variables set via os.environ in the parent are inherited,
    but we set them lazily on demand, so we must redo it here).
    """
    configure_logging()
    configure_langsmith_env()
