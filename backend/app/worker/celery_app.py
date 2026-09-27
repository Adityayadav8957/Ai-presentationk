from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_presentation",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Progress/results are tracked entirely via our own Job rows in Postgres,
    # never via Celery's own result backend — skip it so a terminated task
    # doesn't fail trying to serialize a SystemExit as its "result".
    task_ignore_result=True,
)
