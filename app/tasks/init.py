from celery import Celery

from app.core.config import settings

celery = Celery(
    "tasks",
    broker=settings.celery_broker_url,
)

@celery.task
def test():
    print("test")
