"""
Celery application instance for the backend worker.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "pr002",
    broker=settings.redis_url,
    backend=settings.redis_url.replace("/0", "/1"),
    include=[
        "app.telephony.tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,   # fair scheduling for IO-bound tasks
    beat_schedule={
        "dispatch-due-calls": {
            "task": "telephony.dispatch_due_calls",
            "schedule": 10.0,   # every 10 seconds
        },
        "sweep-stuck-calls": {
            "task": "telephony.sweep_stuck_calls",
            "schedule": 60.0,   # every 60 seconds
        },
    },
)
