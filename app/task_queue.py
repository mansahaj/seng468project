import os

from redis import Redis
from rq import Queue

from app.services.processing import process_document

DOCUMENT_PROCESSING_QUEUE = "document-processing"


def get_redis_connection() -> Redis:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(redis_url)


def get_document_queue() -> Queue:
    return Queue(DOCUMENT_PROCESSING_QUEUE, connection=get_redis_connection())


def enqueue_document_processing(document_id: str) -> str:
    job = get_document_queue().enqueue(process_document, document_id)
    return job.id
