from __future__ import annotations

from celery import Celery

from meridian.settings import settings

celery_app = Celery(__name__, broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_expires = 3600

# Import tasks so Celery can discover them when the worker starts.
import meridian.integrations.tasks  # noqa: F401


def run_worker() -> None:
    """Run a Celery worker instance."""
    celery_app.worker_main(["worker", "--loglevel=info", "--pool=solo"])
