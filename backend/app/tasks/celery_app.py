"""
Celery application. Research runs are dispatched here rather than run
inline in a FastAPI request handler because a full run is many sequential
LLM calls deep (plan -> N parallel specialists -> synthesis -> up to 5
fact-checks -> citations) and can take anywhere from 30 seconds to a few
minutes — long enough that you don't want it tying up a web worker's
event loop, and long enough that it should survive a web server restart
(the Celery worker is a separate process).
"""

from __future__ import annotations

from celery import Celery

from app.config import settings

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
    # A full research run should never legitimately run longer than this;
    # if it does, something's stuck (e.g. an OpenRouter call hanging) and
    # the task should be killed rather than block a worker slot forever.
    task_time_limit=900,
    task_soft_time_limit=840,
    worker_max_tasks_per_child=50,  # periodically recycle workers (embeddings model memory, etc.)
)
