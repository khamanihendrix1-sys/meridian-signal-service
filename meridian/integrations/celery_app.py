from __future__ import annotations

from celery import Celery

from meridian.settings import settings

celery_app = Celery(__name__, broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_expires = 3600
celery_app.autodiscover_tasks(["meridian.integrations"])


def run_worker() -> None:
    """Run a Celery worker instance."""
    celery_app.worker_main(["worker", "--loglevel=info", "--pool=solo"])
