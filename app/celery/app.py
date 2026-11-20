from celery import Celery

from app.core.config import settings

# Kept free of task imports, so code that only sends tasks by name does not import them.
celery = Celery(
    "tasks",
    broker=settings.celery_broker_url,
    include=["app.celery.tasks"],
)

OUTBOX_POLL_SECONDS = 5.0
celery.conf.beat_schedule = {
    "publish-outbox-events": {
        "task": "outbox.publish_pending",
        "schedule": OUTBOX_POLL_SECONDS,
        # A run that waited longer than one interval is replaced by the next one.
        "options": {"expires": OUTBOX_POLL_SECONDS},
    },
    "delete-old-outbox-events": {
        "task": "outbox.delete_old_published",
        "schedule": 3600.0,
    },
}
